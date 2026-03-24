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
from db.tenant_context import set_current_tenant

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


def _make_repo() -> DiarioRepository:
    return DiarioRepository(config.database_url)


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
def verificar_pessoa_task(tenant_id: str, pessoa_id: int) -> None:
    """Verifica uma pessoa específica buscando novas publicações no DJe."""
    set_current_tenant(tenant_id)
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
def first_check_task(tenant_id: str, pessoa_id: int, nome: str, tribunal_filtro: str | None = None) -> None:
    """Executa first check ao cadastrar uma pessoa (salva publicações sem gerar alertas)."""
    set_current_tenant(tenant_id)
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
    Itera por todos os tenants ativos e enfileira verificações por tenant.
    """
    from sqlalchemy import select
    from storage.models import Tenant, PessoaMonitorada

    # Usar repo sem tenant (superuser bypassa RLS)
    repo = DiarioRepository(config.database_url)

    # Buscar todos os tenants ativos (sem RLS)
    with repo.get_session(tenant_id=None) as session:
        tenants = list(session.execute(
            select(Tenant).where(Tenant.is_active == True)
        ).scalars().all())

    if not tenants:
        logger.debug("agendar_verificacoes_task: nenhum tenant ativo")
        return

    for tenant in tenants:
        tid = str(tenant.id)
        try:
            with repo.get_session(tenant_id=tid) as session:
                expirados = repo.desativar_expirados()
                if expirados > 0:
                    logger.info(
                        f"agendar_verificacoes_task: tenant={tid} {expirados} expirado(s) desativado(s)"
                    )
        except Exception as e:
            logger.error(f"agendar_verificacoes_task: erro ao desativar expirados tenant={tid}: {e}")

        # Varrer oportunidades de crédito por tenant
        varrer_oportunidades_task.send(tid)

        pessoas = repo.pessoas_para_verificar_batch()
        if not pessoas:
            continue

        logger.info(f"agendar_verificacoes_task: tenant={tid} enfileirando {len(pessoas)} pessoa(s)")
        for pessoa in pessoas:
            verificar_pessoa_task.send(tid, pessoa.id)


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


def _data_gte(data_str: str, cutoff_str: str) -> bool:
    """Compara datas no formato dd/mm/yyyy ou yyyy-mm-dd. Retorna True se data_str >= cutoff_str."""
    try:
        def _parse(s: str):
            if "-" in s and len(s) == 10 and s[4] == "-":
                return s  # yyyy-mm-dd, já comparável
            parts = s.split("/")
            if len(parts) == 3:
                return f"{parts[2]}-{parts[1]}-{parts[0]}"
            return s
        return _parse(data_str) >= _parse(cutoff_str)
    except Exception:
        return True  # na dúvida, inclui


@dramatiq.actor(
    queue_name="manutencao",
    max_retries=1,
    time_limit=300_000,  # 5 min (inclui classificação LLM)
)
def varrer_oportunidades_task(tenant_id: str | None = None) -> None:
    """Varre publicações recentes buscando sinais de recebimento de valores.
    Gera alertas especiais (OPORTUNIDADE_CREDITO) para cada match ainda não alertado.
    Aplica reranking semântico para descartar falsos positivos antes de criar alertas.
    Enfileira classificação LLM para cada processo distinto detectado.
    """
    from services.embedding_service import rerank_oportunidades
    if tenant_id:
        set_current_tenant(tenant_id)
    repo = DiarioRepository(config.database_url)

    # Buscar janela ampla (90 dias) para classificação de todos os processos visíveis na UI
    candidatos_amplo = repo.buscar_oportunidades(dias=90, limit=500)

    # Filtro semântico: pontuar candidatos e descartar falsos positivos
    if candidatos_amplo:
        pub_ids = [op["id"] for op in candidatos_amplo]
        scores = rerank_oportunidades(pub_ids, threshold=0.45, tenant_id=tenant_id)
        oportunidades_amplo = [op for op in candidatos_amplo if op["id"] in scores]
        for op in oportunidades_amplo:
            op["score_semantico"] = scores[op["id"]]
        descartados = len(candidatos_amplo) - len(oportunidades_amplo)
        if descartados:
            logger.info(
                f"varrer_oportunidades_task: {descartados} publicação(ões) descartadas pelo filtro semântico"
            )
    else:
        oportunidades_amplo = []

    # Agrupar por processo para classificação
    processos_vistos: dict[tuple[int, str], list[dict]] = {}
    for op in oportunidades_amplo:
        key = (op["pessoa_id"], op.get("numero_processo") or "")
        processos_vistos.setdefault(key, []).append(op)

    # Enfileirar classificação LLM para processos ainda não classificados
    if config.openai_habilitado and processos_vistos:
        chaves = [(pid, proc) for pid, proc in processos_vistos if proc]
        classificacoes = repo.obter_classificacoes_batch(chaves)

        enfileirados = 0
        for (pid, proc) in chaves:
            proc_digits = "".join(c for c in proc if c.isdigit())
            classif = classificacoes.get((pid, proc_digits))
            total_pubs = repo.contar_publicacoes_processo(pid, proc)
            if classif and classif["total_pubs"] == total_pubs:
                continue  # Classificação ainda válida
            classificar_processo_task.send(tenant_id or "", pid, proc)
            enfileirados += 1

        if enfileirados:
            logger.info(f"varrer_oportunidades_task: {enfileirados} classificação(ões) enfileirada(s)")

    # Criar alertas apenas para publicações recentes (7 dias)
    from datetime import datetime, timedelta
    cutoff = (datetime.utcnow() - timedelta(days=7)).strftime("%d/%m/%Y")
    oportunidades_recentes = [
        op for op in oportunidades_amplo
        if _data_gte(op.get("data_disponibilizacao", ""), cutoff)
    ]

    classificacoes_atuais = {}
    if processos_vistos:
        chaves_todas = [(pid, proc) for pid, proc in processos_vistos if proc]
        classificacoes_atuais = repo.obter_classificacoes_batch(chaves_todas)

    novas = 0
    for op in oportunidades_recentes:
        if repo.alerta_oportunidade_existe(op["id"]):
            continue
        # Se já classificado como DEVEDOR, não criar alerta
        proc = op.get("numero_processo") or ""
        proc_digits = "".join(c for c in proc if c.isdigit())
        classif = classificacoes_atuais.get((op["pessoa_id"], proc_digits))
        if classif and classif.get("papel") == "DEVEDOR":
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
# FILA: classificacao — Classificação de credor/devedor via LLM
# ============================================================


_CLASSIF_CACHE_TTL = 60 * 60 * 24 * 7  # 7 dias
_CLASSIF_CACHE_VERSION = "v1"


def _classif_cache_key(pessoa_id: int, numero_processo: str, total_pubs: int) -> str:
    digits = "".join(c for c in numero_processo if c.isdigit())
    return f"classif:{_CLASSIF_CACHE_VERSION}:{pessoa_id}:{digits}:{total_pubs}"


@dramatiq.actor(
    queue_name="classificacao",
    max_retries=2,
    min_backoff=5_000,
    time_limit=60_000,  # 1 min
)
def classificar_processo_task(tenant_id: str, pessoa_id: int, numero_processo: str) -> None:
    """Classifica credor/devedor de um processo via LLM (OpenAI).

    Verifica cache Redis → DB → chama OpenAI se necessário.
    Salva resultado em DB e Redis.
    """
    import json as _json

    if not config.openai_habilitado:
        return

    if tenant_id:
        set_current_tenant(tenant_id)
    repo = DiarioRepository(config.database_url)
    publicacoes = repo.buscar_publicacoes_processo(pessoa_id, numero_processo)
    if not publicacoes:
        logger.info(f"classificar_processo_task: sem publicações para pessoa={pessoa_id} proc={numero_processo}")
        return

    total_pubs = len(publicacoes)
    cache_key = _classif_cache_key(pessoa_id, numero_processo, total_pubs)

    # 1. Checar Redis cache
    r = None
    try:
        import redis as _redis
        r = _redis.from_url(config.redis_url, decode_responses=True)
        cached = r.get(cache_key)
        if cached:
            logger.debug(f"classificar_processo_task: cache hit para {cache_key}")
            return
    except Exception as e:
        logger.warning(f"classificar_processo_task: Redis indisponível: {e}")

    # 2. Checar DB
    classif_db = repo.obter_classificacao(pessoa_id, numero_processo)
    if classif_db and classif_db["total_pubs"] == total_pubs:
        # DB tem classificação válida — popular Redis e retornar
        try:
            if r:
                r.setex(cache_key, _CLASSIF_CACHE_TTL, _json.dumps(classif_db, ensure_ascii=False))
        except Exception:
            pass
        logger.debug(f"classificar_processo_task: DB hit para pessoa={pessoa_id} proc={numero_processo}")
        return

    # 3. Chamar OpenAI
    pessoa = repo.obter_pessoa(pessoa_id)
    pessoa_nome = pessoa["nome"] if pessoa else None

    from services.classificacao_service import classificar_processo
    try:
        resultado = classificar_processo(
            publicacoes=publicacoes,
            api_key=config.openai_api_key,
            modelo=config.openai_model,
            pessoa_nome=pessoa_nome,
            numero_processo=numero_processo,
            max_pubs=config.classif_max_pubs,
            max_chars=config.classif_max_chars,
        )
    except RuntimeError as e:
        logger.error(f"classificar_processo_task: falha LLM para pessoa={pessoa_id} proc={numero_processo}: {e}")
        raise

    # 4. Salvar em DB
    repo.salvar_classificacao(
        pessoa_id=pessoa_id,
        numero_processo=numero_processo,
        papel=resultado["papel"],
        veredicto=resultado["veredicto"],
        valor=resultado["valor"],
        justificativa=resultado["justificativa"],
        total_pubs=total_pubs,
    )

    # 5. Salvar em Redis
    try:
        if r:
            cache_data = {
                "pessoa_id": pessoa_id,
                "numero_processo": "".join(c for c in numero_processo if c.isdigit()),
                "papel": resultado["papel"],
                "veredicto": resultado["veredicto"],
                "valor": resultado["valor"],
                "justificativa": resultado["justificativa"],
                "total_pubs": total_pubs,
            }
            r.setex(cache_key, _CLASSIF_CACHE_TTL, _json.dumps(cache_data, ensure_ascii=False))
    except Exception as e:
        logger.warning(f"classificar_processo_task: falha ao salvar Redis: {e}")

    logger.info(
        f"classificar_processo_task: pessoa={pessoa_id} proc={numero_processo} "
        f"→ papel={resultado['papel']} veredicto={resultado['veredicto']}"
    )


# ============================================================
# FILA: indexacao — Vetorização para busca semântica
# ============================================================


@dramatiq.actor(queue_name="indexacao", max_retries=3, min_backoff=5_000)
def indexar_publicacao_task(tenant_id: str, pub_id: int, pub_data: dict) -> None:
    """Vetoriza uma publicação individual e indexa no Qdrant do tenant."""
    from services.embedding_service import index_publicacao, ensure_collections
    if tenant_id:
        set_current_tenant(tenant_id)
    try:
        ensure_collections(tenant_id=tenant_id or None)
        index_publicacao(pub_id, pub_data, tenant_id=tenant_id or None)
    except Exception as e:
        logger.error(f"indexar_publicacao_task: erro ao indexar pub {pub_id}: {e}")
        raise


@dramatiq.actor(queue_name="indexacao", max_retries=3, min_backoff=5_000)
def indexar_processo_task(tenant_id: str, processo_id: str, processo_data: dict) -> None:
    """Vetoriza histórico concatenado de um processo e indexa no Qdrant do tenant."""
    from services.embedding_service import index_processo, ensure_collections
    if tenant_id:
        set_current_tenant(tenant_id)
    try:
        ensure_collections(tenant_id=tenant_id or None)
        index_processo(processo_id, processo_data, tenant_id=tenant_id or None)
    except Exception as e:
        logger.error(f"indexar_processo_task: erro ao indexar processo {processo_id}: {e}")
        raise


@dramatiq.actor(queue_name="indexacao", max_retries=1)
def reindexar_tudo_task(tenant_id: str | None = None) -> None:
    """Backfill: reindexar todas as publicações de um tenant no Qdrant.

    Se tenant_id=None, tenta usar o contexto atual.
    Processa em batches para não sobrecarregar memória.
    """
    from services.embedding_service import ensure_collections, index_publicacoes_batch, index_processos_batch
    from sqlalchemy import select
    from storage.models import Tenant

    if tenant_id:
        set_current_tenant(tenant_id)

    # Resolver tenant_id se não fornecido
    from db.tenant_context import get_current_tenant_or_none
    tid = tenant_id or get_current_tenant_or_none()

    repo = DiarioRepository(config.database_url)

    # Se nenhum tenant, reindexar todos os tenants
    if not tid:
        with repo.get_session(tenant_id=None) as session:
            tenants = list(session.execute(
                select(Tenant).where(Tenant.is_active == True)
            ).scalars().all())
        for t in tenants:
            reindexar_tudo_task.send(str(t.id))
        logger.info(f"reindexar_tudo_task: {len(tenants)} tenant(s) enfileirado(s) para reindex")
        return

    ensure_collections(tenant_id=tid)

    # 1. Indexar publicações em batch
    offset = 0
    batch_size = 20
    total = 0

    while True:
        pubs = repo.get_publicacoes_batch(offset=offset, limit=batch_size)
        if not pubs:
            break
        try:
            items = [(pub.id, pub.to_dict()) for pub in pubs]
            indexados = index_publicacoes_batch(items, tenant_id=tid)
            total += indexados
        except Exception as e:
            logger.error(f"reindexar_tudo_task: erro ao indexar batch offset={offset}: {e}")
        offset += batch_size
        logger.info(f"Reindex publicações tenant={tid}: {total} indexadas...")

    logger.info(f"Reindex publicações tenant={tid} completo: {total} indexadas.")

    # 2. Indexar processos em batch paginado
    proc_offset = 0
    proc_batch_size = 10
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
            indexados = index_processos_batch(processos, tenant_id=tid)
            total_proc += indexados
        except Exception as e:
            logger.error(f"reindexar_tudo_task: erro ao indexar batch de processos offset={proc_offset}: {e}")
        proc_offset += proc_batch_size
        logger.info(f"Reindex processos tenant={tid}: {total_proc} indexados...")

    logger.info(f"Reindex processos tenant={tid} completo: {total_proc} indexados.")


# ---------------------------------------------------------------------------
# Cleanup de Autenticação (manutenção diária)
# ---------------------------------------------------------------------------

@dramatiq.actor(queue_name="manutencao")
def cleanup_expired_auth_tokens():
    """Remove refresh tokens expirados do banco. Roda diariamente.
    Opera cross-tenant (manutenção global).
    """
    try:
        from sqlalchemy import text
        _repo = _make_repo()
        with _repo.get_session() as session:
            result = session.execute(
                text("DELETE FROM refresh_tokens WHERE expires_at < now()")
            )
            session.commit()
            logger.info(f"cleanup_expired_auth_tokens: removidos {result.rowcount} refresh tokens expirados")
    except Exception as e:
        logger.error(f"cleanup_expired_auth_tokens: erro: {e}")


@dramatiq.actor(queue_name="manutencao")
def cleanup_old_audit_logs():
    """Remove audit logs com mais de 90 dias. Roda diariamente.
    Opera cross-tenant (manutenção global).
    """
    try:
        from sqlalchemy import text
        _repo = _make_repo()
        with _repo.get_session() as session:
            result = session.execute(
                text("DELETE FROM auth_audit_log WHERE created_at < now() - interval '90 days'")
            )
            session.commit()
            logger.info(f"cleanup_old_audit_logs: removidos {result.rowcount} registros de audit log")
    except Exception as e:
        logger.error(f"cleanup_old_audit_logs: erro: {e}")
