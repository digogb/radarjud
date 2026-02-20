from fastapi import FastAPI, Query, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import date
import logging
import sys
import os

# Adiciona diretório src ao path para imports funcionarem se rodar direto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from collectors.djen_collector import DJENCollector
from storage.repository import DiarioRepository
from config import Config

# Configuração de Logs básica
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("api")

app = FastAPI(title="DJE Monitor API", version="2.0.0")

# CORS (Permitir frontend react local)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção deve ser restritivo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Inicialização global ---
config = Config()
repo = DiarioRepository(config.database_url)
collector = DJENCollector(tribunal=config.tribunal)

# Broker Dramatiq (apenas enfileira — processamento é feito pelo worker)
from tasks import (
    agendar_verificacoes_task,
    first_check_task,
    broker as dramatiq_broker,
)

# Scheduler APScheduler
_scheduler = None


def _init_scheduler():
    global _scheduler
    if not config.monitor_habilitado:
        logger.info("Monitor de pessoas desabilitado (DJE_MONITOR_HABILITADO=false)")
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        _scheduler = BackgroundScheduler()
        _scheduler.add_job(
            agendar_verificacoes_task.send,  # enfileira no Redis, worker processa
            "interval",
            minutes=config.monitor_interval_minutes,
            id="person_monitor",
            max_instances=1,
            replace_existing=True,
        )
        _scheduler.start()
        logger.info(
            f"Scheduler iniciado — enfileirando verificações a cada {config.monitor_interval_minutes} min"
        )
    except Exception as e:
        logger.error(f"Falha ao iniciar scheduler: {e}")


@app.on_event("startup")
def startup_event():
    _init_scheduler()
    # Garantir collections do Qdrant
    try:
        from services.embedding_service import ensure_collections
        ensure_collections()
        logger.info("Qdrant collections verificadas.")
    except Exception as e:
        logger.warning(f"Qdrant indisponível no startup: {e}")


@app.on_event("shutdown")
def shutdown_event():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler encerrado")


# ============================================================
# Health
# ============================================================

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "dje-monitor-api"}


# ============================================================
# Busca (existente)
# ============================================================

@app.get("/api/v1/search")
async def search_name(
    nome: str = Query(..., min_length=3, description="Nome da parte a ser buscada"),
    tribunal: Optional[str] = Query(None, description="Filtro opcional de tribunal"),
):
    """Busca comunicações no DJEN pelo nome da parte."""
    logger.info(f"Recebida busca por nome: {nome}")
    try:
        hoje = date.today()
        resultados = collector.buscar_por_nome(nome, hoje, hoje)
        resultados = [
            r for r in resultados
            if not (r.get("siglaTribunal") or r.get("tribunal", "")).upper().startswith("TRF")
        ]
        if tribunal:
            resultados = [
                r for r in resultados
                if (r.get("siglaTribunal") or r.get("tribunal", "")).upper() == tribunal.upper()
            ]
        return {"count": len(resultados), "results": resultados}
    except Exception as e:
        logger.error(f"Erro na busca API: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Pessoas Monitoradas
# ============================================================

class PessoaMonitoradaCreate(BaseModel):
    nome: str
    cpf: Optional[str] = None
    tribunal_filtro: Optional[str] = None
    intervalo_horas: int = 12


class PessoaMonitoradaUpdate(BaseModel):
    nome: Optional[str] = None
    cpf: Optional[str] = None
    tribunal_filtro: Optional[str] = None
    intervalo_horas: Optional[int] = None
    ativo: Optional[bool] = None


@app.post("/api/v1/pessoas-monitoradas", status_code=201)
def criar_pessoa(body: PessoaMonitoradaCreate):
    """
    Cria uma pessoa para monitoramento.
    Enfileira first_check no worker Dramatiq (salva publicações existentes sem gerar alertas).
    """
    pessoa = repo.adicionar_pessoa(
        nome=body.nome,
        cpf=body.cpf,
        tribunal_filtro=body.tribunal_filtro,
        intervalo_horas=body.intervalo_horas,
    )
    # First check assíncrono: enfileira no worker
    first_check_task.send(pessoa.id, pessoa.nome, pessoa.tribunal_filtro)
    return repo.obter_pessoa(pessoa.id)


@app.get("/api/v1/pessoas-monitoradas")
def listar_pessoas(ativo: Optional[bool] = Query(None)):
    """Lista pessoas monitoradas."""
    apenas_ativas = ativo if ativo is not None else True
    pessoas = repo.listar_pessoas(apenas_ativas=apenas_ativas)
    return {"count": len(pessoas), "items": pessoas}


@app.get("/api/v1/pessoas-monitoradas/{pessoa_id}")
def obter_pessoa(pessoa_id: int):
    """Retorna detalhes de uma pessoa monitorada."""
    pessoa = repo.obter_pessoa(pessoa_id)
    if not pessoa:
        raise HTTPException(status_code=404, detail="Pessoa não encontrada")
    return pessoa


@app.put("/api/v1/pessoas-monitoradas/{pessoa_id}")
def atualizar_pessoa(pessoa_id: int, body: PessoaMonitoradaUpdate):
    """Atualiza dados de uma pessoa monitorada."""
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    pessoa = repo.atualizar_pessoa(pessoa_id, **updates)
    if not pessoa:
        raise HTTPException(status_code=404, detail="Pessoa não encontrada")
    return pessoa


@app.delete("/api/v1/pessoas-monitoradas/{pessoa_id}", status_code=204)
def desativar_pessoa(pessoa_id: int):
    """Desativa monitoramento de uma pessoa (soft delete)."""
    ok = repo.desativar_pessoa(pessoa_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Pessoa não encontrada")


@app.get("/api/v1/pessoas-monitoradas/{pessoa_id}/publicacoes")
def listar_publicacoes_pessoa(pessoa_id: int, limit: int = Query(100, le=500)):
    """Lista publicações encontradas para uma pessoa monitorada."""
    pessoa = repo.obter_pessoa(pessoa_id)
    if not pessoa:
        raise HTTPException(status_code=404, detail="Pessoa não encontrada")
    return repo.listar_publicacoes_pessoa(pessoa_id, limit=limit)


@app.get("/api/v1/pessoas-monitoradas/{pessoa_id}/alertas")
def listar_alertas_pessoa(pessoa_id: int, lido: Optional[bool] = Query(None), limit: int = 50):
    """Lista alertas de uma pessoa monitorada."""
    pessoa = repo.obter_pessoa(pessoa_id)
    if not pessoa:
        raise HTTPException(status_code=404, detail="Pessoa não encontrada")
    return repo.listar_alertas(pessoa_id=pessoa_id, lido=lido, limit=limit)


# ============================================================
# Alertas
# ============================================================

class MarcarLidosBody(BaseModel):
    ids: Optional[List[int]] = None
    todos: bool = False


@app.get("/api/v1/alertas")
def listar_alertas(
    pessoa_id: Optional[int] = Query(None),
    lido: Optional[bool] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = 0,
):
    """Lista alertas com filtros opcionais."""
    return repo.listar_alertas(pessoa_id=pessoa_id, lido=lido, limit=limit, offset=offset)


@app.get("/api/v1/alertas/nao-lidos/count")
def contar_alertas_nao_lidos(pessoa_id: Optional[int] = Query(None)):
    """Retorna contagem de alertas não lidos para badge."""
    return {"count": repo.contar_alertas_nao_lidos(pessoa_id=pessoa_id)}


@app.post("/api/v1/alertas/marcar-lidos")
def marcar_alertas_lidos(body: MarcarLidosBody):
    """Marca alertas como lidos."""
    count = repo.marcar_alertas_lidos(ids=body.ids, todos=body.todos)
    return {"marcados": count}


# ============================================================
# Dashboard (substituindo mocks)
# ============================================================

@app.get("/api/dashboard/resumo")
def dashboard_resumo():
    return repo.dashboard_stats()


@app.get("/api/dashboard/alteracoes")
def dashboard_alteracoes(limit: int = 10):
    return repo.alertas_recentes_dashboard(limit=limit)


@app.post("/api/dashboard/alteracoes/marcar-vistas")
def dashboard_marcar_vistas(body: dict = {}):
    ids = body.get("ids")
    count = repo.marcar_alertas_lidos(ids=ids, todos=(ids is None))
    return {"marcados": count}


@app.get("/api/dashboard/estatisticas/tribunais")
def dashboard_stats_tribunais():
    return []


# ============================================================
# Sync
# ============================================================

@app.post("/api/sync/forcar")
def forcar_sync():
    """Força verificação imediata de todas as pessoas enfileirando via Dramatiq."""
    agendar_verificacoes_task.send()
    return {"status": "iniciado", "mensagem": "Verificação enfileirada no worker"}


@app.get("/api/sync/status")
def sync_status():
    """Retorna status do scheduler e informações das filas Redis."""
    scheduler_info = {
        "ativo": False,
        "proxima_execucao": None,
        "interval_minutes": config.monitor_interval_minutes,
    }

    if _scheduler is not None:
        jobs = _scheduler.get_jobs()
        proxima = None
        if jobs:
            proxima = jobs[0].next_run_time.isoformat() if jobs[0].next_run_time else None
        scheduler_info["ativo"] = _scheduler.running
        scheduler_info["proxima_execucao"] = proxima

    # Contagem de mensagens pendentes nas filas Redis
    filas = {}
    try:
        import redis as redis_client
        r = redis_client.from_url(config.redis_url)
        for fila in ["verificacao", "scheduler", "manutencao", "indexacao"]:
            count = r.llen(f"dramatiq:{fila}")
            filas[fila] = int(count)
    except Exception as e:
        logger.warning(f"Não foi possível consultar filas Redis: {e}")
        filas = {"erro": str(e)}

    return {**scheduler_info, "filas": filas}


# ============================================================
# Importação de Planilha
# ============================================================

@app.post("/api/v1/importar-planilha")
async def importar_planilha_endpoint(
    arquivo: UploadFile = File(...),
    dry_run: bool = Query(False, description="Simula sem gravar no banco"),
    desativar_expirados: bool = Query(False, description="Desativa monitoramentos expirados após importar"),
    intervalo_horas: int = Query(24, description="Frequência de verificação em horas (6, 12, 24 ou 48)"),
):
    """Faz upload de pessoas.xlsx e importa partes adversas como pessoas monitoradas.
    Retorna os stats da importação ao concluir (síncrono).
    """
    logger.info(f"Iniciando upload de planilha: {arquivo.filename}")
    
    import tempfile
    import shutil
    import traceback
    from services.import_pessoas import importar_planilha

    if not arquivo.filename or not arquivo.filename.endswith(".xlsx"):
        logger.warning(f"Tentativa de upload de arquivo inválido: {arquivo.filename}")
        raise HTTPException(status_code=400, detail="Arquivo deve ser .xlsx")

    try:
        # Salva o arquivo temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            shutil.copyfileobj(arquivo.file, tmp)
            tmp_path = tmp.name

        logger.info(f"Arquivo salvo temporariamente em: {tmp_path}")

        # Executa a importação
        logger.info(f"Chamando importar_planilha(dry_run={dry_run})...")
        stats = importar_planilha(tmp_path, repo, dry_run=dry_run, intervalo_horas=intervalo_horas)
        logger.info(f"Importação concluída. Stats: {stats}")
        if desativar_expirados and not dry_run:
            logger.info("Desativando monitoramentos expirados...")
            stats["expirados_desativados"] = repo.desativar_expirados()
            logger.info(f"Expirados desativados: {stats.get('expirados_desativados')}")

        return {"dry_run": dry_run, **stats}

    except Exception as e:
        logger.error(f"Erro fatal na importação de planilha: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erro interno ao processar planilha: {str(e)}")
        
    finally:
        try:
            if 'tmp_path' in locals():
                os.unlink(tmp_path)
        except Exception:
            pass


# ============================================================
# Busca Semântica (Qdrant)
# ============================================================


@app.get("/api/v1/search/semantic")
def semantic_search(
    q: str = Query(..., min_length=3, description="Texto da busca semântica"),
    tribunal: Optional[str] = Query(None, description="Filtro por tribunal (ex: TJCE)"),
    pessoa_id: Optional[int] = Query(None, description="Filtro por pessoa monitorada"),
    limit: int = Query(20, ge=1, le=100),
    score_threshold: float = Query(0.35, ge=0.0, le=1.0),
    tipo: str = Query("publicacoes", regex="^(publicacoes|processos)$"),
):
    """
    Busca semântica em publicações ou processos.

    - **q**: Texto da busca (ex: "execução fiscal dívida tributária")
    - **tribunal**: Filtro por tribunal (ex: TJCE)
    - **pessoa_id**: Filtro por pessoa monitorada
    - **limit**: Máximo de resultados (1-100)
    - **score_threshold**: Score mínimo de similaridade (0.0-1.0)
    - **tipo**: "publicacoes" ou "processos"
    """
    from services.embedding_service import search_publicacoes, search_processos
    try:
        if tipo == "processos":
            results = search_processos(
                query=q, tribunal=tribunal,
                limit=limit, score_threshold=score_threshold,
            )
        else:
            results = search_publicacoes(
                query=q, tribunal=tribunal, pessoa_id=pessoa_id,
                limit=limit, score_threshold=score_threshold,
            )
        return {
            "query": q,
            "tipo": tipo,
            "total": len(results),
            "results": results,
        }
    except Exception as e:
        logger.error(f"Erro na busca semântica: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Serviço de busca semântica indisponível: {str(e)}")


@app.post("/api/v1/search/reindex")
def trigger_reindex():
    """Dispara reindexação completa das publicações no Qdrant."""
    from tasks import reindexar_tudo_task
    reindexar_tudo_task.send()
    return {"status": "reindex enfileirado"}


@app.get("/api/v1/search/semantic/status")
def semantic_status():
    """Retorna status do Qdrant e contadores das collections."""
    try:
        from services.embedding_service import get_client
        client = get_client()
        collections = {}
        for c in client.get_collections().collections:
            info = client.get_collection(c.name)
            collections[c.name] = {
                "points": info.points_count,
                "vectors": info.vectors_count,
                "status": info.status.value,
            }
        return {"status": "ok", "collections": collections}
    except Exception as e:
        return {"status": "error", "message": str(e)}
