"""
Definição das tarefas Dramatiq para processamento assíncrono.

Cada actor é executado pelo worker (python -m dramatiq tasks).
A API apenas enfileira tarefas via .send() — não executa diretamente.
"""

import logging
import os
import sys

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AgeLimit, Retries, TimeLimit

# Garante que o diretório src está no path quando rodando como módulo
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from storage.repository import DiarioRepository
from services.monitor_service import MonitorService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuração do broker Redis
# ---------------------------------------------------------------------------

config = Config()

broker = RedisBroker(
    url=config.redis_url,
    middleware=[
        AgeLimit(),
        TimeLimit(),
        Retries(max_retries=3, min_backoff=10_000, max_backoff=60_000),
    ],
)
dramatiq.set_broker(broker)


# ---------------------------------------------------------------------------
# Fábrica de serviço (cada chamada cria instância isolada com sessão própria)
# ---------------------------------------------------------------------------

def _make_service() -> MonitorService:
    repo = DiarioRepository(config.database_url)
    return MonitorService(repo=repo, config=config)


# ---------------------------------------------------------------------------
# Actors
# ---------------------------------------------------------------------------

@dramatiq.actor(
    queue_name="verificacao",
    max_retries=3,
    min_backoff=10_000,
    max_backoff=60_000,
    time_limit=300_000,  # 5 min por pessoa
)
def verificar_pessoa_task(pessoa_id: int) -> None:
    """Verifica uma pessoa específica buscando novas publicações no DJe."""
    service = _make_service()
    pessoa = service.repo.obter_pessoa_orm(pessoa_id)
    if not pessoa:
        logger.warning(f"verificar_pessoa_task: pessoa {pessoa_id} não encontrada, ignorando")
        return
    if not pessoa.ativo:
        logger.info(f"verificar_pessoa_task: pessoa {pessoa_id} inativa, ignorando")
        return
    try:
        novos = service.verificar_pessoa(pessoa)
        logger.info(f"verificar_pessoa_task: {pessoa.nome} — {novos} nova(s) publicação(ões)")
    finally:
        service.repo.atualizar_ultimo_check(pessoa_id)


@dramatiq.actor(
    queue_name="verificacao",
    max_retries=1,
    time_limit=600_000,  # 10 min para first check
)
def first_check_task(pessoa_id: int, nome: str, tribunal_filtro: str | None = None) -> None:
    """Executa first check ao cadastrar uma pessoa (salva publicações sem gerar alertas)."""
    service = _make_service()
    total = service.first_check(pessoa_id, nome, tribunal_filtro)
    logger.info(f"first_check_task: {nome} — {total} publicação(ões) salvas")


@dramatiq.actor(
    queue_name="scheduler",
    max_retries=0,
    time_limit=60_000,  # 1 min para enfileirar todas as pessoas
)
def agendar_verificacoes_task() -> None:
    """
    Chamada pelo APScheduler da API a cada N minutos.
    Consulta pessoas_para_verificar() e enfileira uma task por pessoa.
    """
    repo = DiarioRepository(config.database_url)

    # Desativa expirados antes de enfileirar
    try:
        expirados = repo.desativar_expirados()
        if expirados > 0:
            logger.info(f"agendar_verificacoes_task: {expirados} monitoramento(s) expirado(s) desativado(s)")
    except Exception as e:
        logger.error(f"agendar_verificacoes_task: erro ao desativar expirados: {e}")

    # Varrer oportunidades de crédito a cada ciclo de sync
    varrer_oportunidades_task.send()

    pessoas = repo.pessoas_para_verificar_batch()
    if not pessoas:
        logger.debug("agendar_verificacoes_task: nenhuma pessoa para verificar")
        return

    logger.info(f"agendar_verificacoes_task: enfileirando {len(pessoas)} pessoa(s)")
    for pessoa in pessoas:
        verificar_pessoa_task.send(pessoa.id)


@dramatiq.actor(
    queue_name="manutencao",
    max_retries=0,
    time_limit=30_000,
)
def desativar_expirados_task() -> None:
    """Desativa monitoramentos cujo prazo de 5 anos expirou."""
    repo = DiarioRepository(config.database_url)
    expirados = repo.desativar_expirados()
    logger.info(f"desativar_expirados_task: {expirados} monitoramento(s) desativado(s)")


# ============================================================
# FILA: manutencao — Oportunidades de Crédito
# ============================================================


@dramatiq.actor(
    queue_name="manutencao",
    max_retries=1,
    time_limit=120_000,  # 2 min
)
def varrer_oportunidades_task() -> None:
    """Varre publicações recentes buscando sinais de recebimento de valores.
    Gera alertas especiais (OPORTUNIDADE_CREDITO) para cada match ainda não alertado.
    Aplica reranking semântico para descartar falsos positivos antes de criar alertas.
    """
    from services.embedding_service import rerank_oportunidades
    repo = DiarioRepository(config.database_url)
    candidatos = repo.buscar_oportunidades(dias=7, limit=500)

    # Filtro semântico: pontuar candidatos e descartar falsos positivos
    if candidatos:
        pub_ids = [op["id"] for op in candidatos]
        scores = rerank_oportunidades(pub_ids, threshold=0.45)
        oportunidades = [op for op in candidatos if op["id"] in scores]
        descartados = len(candidatos) - len(oportunidades)
        if descartados:
            logger.info(
                f"varrer_oportunidades_task: {descartados} publicação(ões) descartadas pelo filtro semântico"
            )
    else:
        oportunidades = []

    novas = 0
    for op in oportunidades:
        if repo.alerta_oportunidade_existe(op["id"]):
            continue
        titulo = f"Oportunidade: {op['padrao_detectado']} | {op['tribunal']}"
        descricao = f"{op['pessoa_nome']} — {(op.get('texto_resumo') or '')[:300]}"
        repo.registrar_alerta(
            pessoa_id=op["pessoa_id"],
            publicacao_id=op["id"],
            tipo="OPORTUNIDADE_CREDITO",
            titulo=titulo,
            descricao=descricao,
        )
        novas += 1
    logger.info(f"varrer_oportunidades_task: {novas} nova(s) oportunidade(s) detectada(s)")


# ============================================================
# FILA: indexacao — Vetorização para busca semântica
# ============================================================


@dramatiq.actor(queue_name="indexacao", max_retries=3, min_backoff=5_000)
def indexar_publicacao_task(pub_id: int, pub_data: dict) -> None:
    """Vetoriza uma publicação individual e indexa no Qdrant."""
    from services.embedding_service import index_publicacao, ensure_collections
    try:
        ensure_collections()
        index_publicacao(pub_id, pub_data)
    except Exception as e:
        logger.error(f"indexar_publicacao_task: erro ao indexar pub {pub_id}: {e}")
        raise


@dramatiq.actor(queue_name="indexacao", max_retries=3, min_backoff=5_000)
def indexar_processo_task(processo_id: str, processo_data: dict) -> None:
    """Vetoriza histórico concatenado de um processo e indexa no Qdrant."""
    from services.embedding_service import index_processo, ensure_collections
    try:
        ensure_collections()
        index_processo(processo_id, processo_data)
    except Exception as e:
        logger.error(f"indexar_processo_task: erro ao indexar processo {processo_id}: {e}")
        raise


@dramatiq.actor(queue_name="indexacao", max_retries=1)
def reindexar_tudo_task() -> None:
    """Backfill: reindexar todas as publicações existentes no Qdrant.
    Processa em batches para não sobrecarregar memória.
    Usa batch encode + batch upsert para máxima eficiência.
    """
    from services.embedding_service import ensure_collections, index_publicacoes_batch, index_processos_batch

    ensure_collections()
    repo = DiarioRepository(config.database_url)

    # 1. Indexar publicações em batch
    offset = 0
    batch_size = 100
    total = 0

    while True:
        pubs = repo.get_publicacoes_batch(offset=offset, limit=batch_size)
        if not pubs:
            break
        try:
            items = [(pub.id, pub.to_dict()) for pub in pubs]
            indexados = index_publicacoes_batch(items)
            total += indexados
        except Exception as e:
            logger.error(f"reindexar_tudo_task: erro ao indexar batch offset={offset}: {e}")
        offset += batch_size
        logger.info(f"Reindex publicações: {total} indexadas...")

    logger.info(f"Reindex publicações completo: {total} indexadas.")

    # 2. Indexar processos em batch paginado (evita carregar tudo em memória)
    proc_offset = 0
    proc_batch_size = 50
    total_proc = 0

    while True:
        numeros = repo.get_distinct_processos_batch(offset=proc_offset, limit=proc_batch_size)
        if not numeros:
            break
        processos = []
        for numero in numeros:
            proc_data = repo.get_publicacoes_por_processo(numero)
            if proc_data:
                processos.append(proc_data)
        try:
            indexados = index_processos_batch(processos)
            total_proc += indexados
        except Exception as e:
            logger.error(f"reindexar_tudo_task: erro ao indexar batch de processos offset={proc_offset}: {e}")
        proc_offset += proc_batch_size
        logger.info(f"Reindex processos: {total_proc} indexados...")

    logger.info(f"Reindex processos completo: {total_proc} indexados.")
