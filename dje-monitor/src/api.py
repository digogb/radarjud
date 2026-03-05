from fastapi import FastAPI, Query, HTTPException, BackgroundTasks, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Any
import logging
import re
import sys
import os

# Adiciona diretório src ao path para imports funcionarem se rodar direto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from collectors.djen_collector import DJENCollector
from storage.repository import DiarioRepository
from config import Config
from middleware.tenant import TenantMiddleware
from auth.token_service import TokenService
from auth.auth_service import AuthService
from auth.dependencies import set_token_service

# Configuração de Logs básica
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("api")

app = FastAPI(title="DJE Monitor API", version="2.0.0")

# Security Headers
from middleware.security_headers import SecurityHeadersMiddleware
app.add_middleware(SecurityHeadersMiddleware)

# CORS
_cors_origins = ["http://localhost:5173", "http://localhost:3000", "http://localhost:80"]
_extra_origins = os.getenv("DJE_CORS_ORIGINS", "").split(",")
_cors_origins += [o.strip() for o in _extra_origins if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Inicialização global ---
config = Config()
repo = DiarioRepository(config.database_url)
collector = DJENCollector(tribunal=config.tribunal)

# Auth (JWT + serviços)
_token_service = None
_auth_service = None
_rate_limiter = None
if config.auth_habilitado:
    _token_service = TokenService(
        secret_key=config.jwt_secret_key,
        algorithm=config.jwt_algorithm,
        access_expire_minutes=config.access_token_expire_minutes,
        refresh_expire_days=config.refresh_token_expire_days,
    )
    set_token_service(_token_service)
    _auth_service = AuthService(
        session_factory=repo.get_session,
        token_service=_token_service,
        max_login_attempts=config.max_login_attempts,
        lockout_minutes=config.lockout_minutes,
    )

    from middleware.rate_limit import LoginRateLimiter
    _rate_limiter = LoginRateLimiter(
        redis_url=config.redis_url,
        max_attempts=config.login_rate_limit_attempts,
        window_seconds=config.login_rate_limit_window_seconds,
    )

# Tenant Middleware — identifica tenant via X-Tenant-ID ou Bearer JWT
app.add_middleware(TenantMiddleware, get_session_fn=repo.get_session, token_service=_token_service)

# Router Admin (gerenciamento de tenants — não usa middleware de tenant)
from routers import admin as admin_router_module
admin_router_module._get_session_fn = repo.get_session
app.include_router(admin_router_module.router)

# Router Auth
from routers import auth as auth_router_module
if _auth_service:
    auth_router_module.set_auth_service(_auth_service)
if _rate_limiter:
    auth_router_module.set_rate_limiter(_rate_limiter)
app.include_router(auth_router_module.router, prefix="/auth")

# Router Users
from routers import users as users_router_module
from services.user_service import UserService
_user_service = UserService(session_factory=repo.get_session)
users_router_module.set_user_service(_user_service)
app.include_router(users_router_module.router, prefix="/users")

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
        # Reindex diário de madrugada (garante consistência do Qdrant após falhas incrementais)
        try:
            from tasks import reindexar_tudo_task
            _scheduler.add_job(
                reindexar_tudo_task.send,
                "cron", hour=2, minute=0,
                id="reindex_diario",
                max_instances=1, replace_existing=True,
            )
            logger.info("Reindex diário agendado para 02:00")
        except Exception as e_reindex:
            logger.warning(f"Não foi possível agendar reindex diário: {e_reindex}")

        # Cleanup diário de tokens expirados e audit logs
        try:
            from tasks import cleanup_expired_auth_tokens, cleanup_old_audit_logs
            _scheduler.add_job(
                cleanup_expired_auth_tokens.send,
                "cron", hour=3, minute=0,
                id="cleanup_auth_tokens",
                max_instances=1, replace_existing=True,
            )
            _scheduler.add_job(
                cleanup_old_audit_logs.send,
                "cron", hour=3, minute=30,
                id="cleanup_audit_logs",
                max_instances=1, replace_existing=True,
            )
        except Exception as e_cleanup:
            logger.warning(f"Não foi possível agendar cleanup de auth: {e_cleanup}")

        _scheduler.start()
        logger.info(
            f"Scheduler iniciado — enfileirando verificações a cada {config.monitor_interval_minutes} min"
        )
    except Exception as e:
        logger.error(f"Falha ao iniciar scheduler: {e}")


@app.on_event("startup")
def startup_event():
    _init_scheduler()
    # Seed padrões de oportunidade (só insere se tabela vazia)
    try:
        repo.seed_padroes_oportunidade()
    except Exception as e:
        logger.warning(f"Não foi possível fazer seed de padrões: {e}")
    # Garantir collections do Qdrant
    try:
        from services.embedding_service import ensure_collections
        ensure_collections()
        logger.info("Qdrant collections verificadas.")
    except Exception as e:
        logger.warning(f"Qdrant/Embedding indisponível no startup: {e}")


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
        resultados = collector.buscar_por_nome(nome)
        resultados = [
            r for r in resultados
            if not (r.get("siglaTribunal") or r.get("tribunal", "")).upper().startswith("TRF")
        ]
        if tribunal:
            resultados = [
                r for r in resultados
                if (r.get("siglaTribunal") or r.get("tribunal", "")).upper() == tribunal.upper()
            ]

        # Remover processos de referência das pessoas monitoradas com esse nome
        processos_referencia: set[str] = set()
        try:
            from storage.models import PessoaMonitorada as _PessoaModel
            from utils.data_normalizer import normalizar_nome as _norm
            nome_norm = _norm(nome)
            with repo.get_session() as session:
                candidatos = (
                    session.query(_PessoaModel.nome, _PessoaModel.numero_processo)
                    .filter(_PessoaModel.ativo == True, _PessoaModel.numero_processo != None)
                    .all()
                )
                for p_nome, p_proc in candidatos:
                    if _norm(p_nome) == nome_norm and p_proc:
                        processos_referencia.add(re.sub(r"\D", "", p_proc))
        except Exception as e_ref:
            logger.warning(f"Não foi possível buscar processos referência: {e_ref}")

        if processos_referencia:
            antes = len(resultados)
            resultados = [
                r for r in resultados
                if re.sub(r"\D", "", r.get("processo", "")) not in processos_referencia
            ]
            logger.info(f"Filtro de processos referência: {antes} → {len(resultados)} resultados")

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
def criar_pessoa(request: Request, body: PessoaMonitoradaCreate):
    """
    Cria uma pessoa para monitoramento.
    Enfileira first_check no worker Dramatiq (salva publicações existentes sem gerar alertas).
    """
    _tid = getattr(request.state, "tenant_id", "")
    pessoa = repo.adicionar_pessoa(
        nome=body.nome,
        cpf=body.cpf,
        tribunal_filtro=body.tribunal_filtro,
        intervalo_horas=body.intervalo_horas,
    )
    # First check assíncrono: enfileira no worker
    first_check_task.send(_tid, pessoa.id, pessoa.nome, pessoa.tribunal_filtro)
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
    """Lista publicações encontradas para uma pessoa monitorada, agrupadas por processo.

    O processo de referência (numero_processo da pessoa) é excluído da listagem —
    ele aparece apenas no cabeçalho da pessoa monitorada.
    """
    pessoa = repo.obter_pessoa(pessoa_id)
    if not pessoa:
        raise HTTPException(status_code=404, detail="Pessoa não encontrada")
    processo_referencia = pessoa.get("numero_processo")
    return repo.listar_publicacoes_pessoa(
        pessoa_id, limit=limit, excluir_processo=processo_referencia
    )


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
def contar_alertas_nao_lidos(
    pessoa_id: Optional[int] = Query(None),
    tipo: Optional[str] = Query(None, description="Filtrar por tipo de alerta (ex: OPORTUNIDADE_CREDITO)"),
):
    """Retorna contagem de alertas não lidos para badge."""
    return {"count": repo.contar_alertas_nao_lidos(pessoa_id=pessoa_id, tipo=tipo)}


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
    request: Request,
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
    import time as _time
    from services.embedding_service import search_publicacoes, search_processos
    from storage.models import PublicacaoMonitorada
    _t_start = _time.perf_counter()
    _tenant_id = getattr(request.state, "tenant_id", None)
    try:
        # Coletar processos de referência para excluir dos resultados
        processos_referencia: set[str] = set()
        try:
            from storage.models import PessoaMonitorada as _PessoaModel
            with repo.get_session() as session:
                procs = (
                    session.query(_PessoaModel.numero_processo)
                    .filter(_PessoaModel.ativo == True, _PessoaModel.numero_processo != None)
                    .all()
                )
                for (proc,) in procs:
                    digits = re.sub(r"\D", "", proc)
                    if digits:
                        processos_referencia.add(digits)
        except Exception as e_ref:
            logger.warning(f"Não foi possível buscar processos referência para filtro semântico: {e_ref}")

        if tipo == "processos":
            results = search_processos(
                query=q, tribunal=tribunal,
                limit=limit, score_threshold=score_threshold,
                tenant_id=_tenant_id,
            )
            # Enriquecer processos com publicações completas do PostgreSQL
            numeros = [r.get("numero_processo") for r in results if r.get("numero_processo")]
            if numeros:
                with repo.get_session() as session:
                    pubs = (
                        session.query(PublicacaoMonitorada)
                        .filter(PublicacaoMonitorada.numero_processo.in_(numeros))
                        .order_by(PublicacaoMonitorada.data_disponibilizacao.desc())
                        .all()
                    )
                    # Agrupar publicações por numero_processo
                    pubs_por_processo: dict = {}
                    for p in pubs:
                        key = p.numero_processo
                        if key not in pubs_por_processo:
                            pubs_por_processo[key] = []
                        d = p.to_dict()
                        pubs_por_processo[key].append({
                            "id": d.get("id"),
                            "texto_resumo": (d.get("texto_resumo") or "")[:300],
                            "texto_completo": d.get("texto_completo", ""),
                            "data_disponibilizacao": d.get("data_disponibilizacao", ""),
                            "orgao": d.get("orgao", ""),
                            "tipo_comunicacao": d.get("tipo_comunicacao", ""),
                            "link": d.get("link", ""),
                            "polo_ativo": d.get("polo_ativo", ""),
                            "polo_passivo": d.get("polo_passivo", ""),
                        })
                for r in results:
                    r["publicacoes"] = pubs_por_processo.get(r.get("numero_processo"), [])
                    r["total_publicacoes"] = len(r["publicacoes"])
        else:
            results = search_publicacoes(
                query=q, tribunal=tribunal, pessoa_id=pessoa_id,
                limit=limit, score_threshold=score_threshold,
                tenant_id=_tenant_id,
            )
            # Enriquecer com dados completos do PostgreSQL
            pub_ids = [r["pub_id"] for r in results]
            if pub_ids:
                with repo.get_session() as session:
                    pubs = session.query(PublicacaoMonitorada).filter(
                        PublicacaoMonitorada.id.in_(pub_ids)
                    ).all()
                    pub_map = {p.id: p.to_dict() for p in pubs}
                for r in results:
                    full = pub_map.get(r["pub_id"], {})
                    if full:
                        r["texto_completo"] = full.get("texto_completo", "")
                        r["texto_resumo"] = full.get("texto_resumo", "")
                        r["polos"] = full.get("polos", {})
                        r["link"] = full.get("link", "")
                        r["data_disponibilizacao"] = full.get("data_disponibilizacao", "")
                        r["orgao"] = full.get("orgao", "")
                        r["numero_processo"] = full.get("numero_processo", "")
                        r["tribunal"] = full.get("tribunal", "")
                        r["tipo_comunicacao"] = full.get("tipo_comunicacao", "")
        # Filtrar processos de referência dos resultados
        if processos_referencia:
            campo = "numero_processo"
            antes = len(results)
            results = [
                r for r in results
                if re.sub(r"\D", "", r.get(campo, "")) not in processos_referencia
            ]
            if antes != len(results):
                logger.info(f"Busca semântica: {antes} → {len(results)} após filtro de processos referência")

        _t_total = (_time.perf_counter() - _t_start) * 1000
        logger.info(
            f"[SEMANTIC:endpoint] tipo={tipo} resultados={len(results)} "
            f"total={_t_total:.0f}ms"
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


# ============================================================
# Oportunidades de Crédito
# ============================================================


@app.get("/api/v1/oportunidades")
def buscar_oportunidades(
    request: Request,
    dias: int = Query(30, ge=1, le=365, description="Janela de dias para varrer publicações"),
    limit: int = Query(50, ge=1, le=200, description="Máximo de resultados"),
    semantico: bool = Query(True, description="Aplicar filtro semântico para reduzir falsos positivos"),
):
    """Lista publicações recentes com sinais de recebimento de valores (alvará, levantamento, precatório).

    Com `semantico=true` (padrão), aplica reranking via Qdrant para filtrar resultados com baixa
    relevância semântica, reduzindo falsos positivos do matching por palavra-chave.

    Cada item é enriquecido com classificação IA (ia_papel, ia_veredicto, ia_valor) quando disponível.
    """
    _tenant_id = getattr(request.state, "tenant_id", None)
    items = repo.buscar_oportunidades(dias=dias, limit=limit)
    if semantico and items:
        from services.embedding_service import rerank_oportunidades
        pub_ids = [item["id"] for item in items]
        scores = rerank_oportunidades(pub_ids, threshold=0.45, tenant_id=_tenant_id)
        items = [item for item in items if item["id"] in scores]
        for item in items:
            item["score_semantico"] = scores[item["id"]]

    # Enriquecer com classificações IA e descartadas pelo usuário (batch)
    if items:
        chaves = list({(item["pessoa_id"], item.get("numero_processo") or "") for item in items})
        chaves = [(pid, proc) for pid, proc in chaves if proc]
        classificacoes = repo.obter_classificacoes_batch(chaves) if chaves else {}
        descartadas = repo.obter_descartadas_batch(chaves) if chaves else set()
        for item in items:
            proc = item.get("numero_processo") or ""
            proc_digits = "".join(c for c in proc if c.isdigit())
            classif = classificacoes.get((item["pessoa_id"], proc_digits))
            if classif:
                item["ia_papel"] = classif["papel"]
                item["ia_veredicto"] = classif["veredicto"]
                item["ia_valor"] = classif["valor"]
                item["ia_justificativa"] = classif["justificativa"]
            else:
                item["ia_papel"] = None
                item["ia_veredicto"] = None
                item["ia_valor"] = None
                item["ia_justificativa"] = None
            item["descartado_por_usuario"] = (item["pessoa_id"], proc_digits) in descartadas

    return {"total": len(items), "items": items}


@app.get("/api/v1/padroes-oportunidade")
def listar_padroes():
    """Lista padrões de detecção de oportunidades configurados."""
    return repo.listar_padroes_oportunidade()


class PadraoCreate(BaseModel):
    nome: str
    expressao: str
    tipo: str = 'positivo'  # 'positivo' ou 'negativo'


class PadraoUpdate(BaseModel):
    nome: Optional[str] = None
    expressao: Optional[str] = None
    tipo: Optional[str] = None
    ativo: Optional[bool] = None
    ordem: Optional[int] = None


class PadraoReordenar(BaseModel):
    ids: List[int]


@app.post("/api/v1/padroes-oportunidade", status_code=201)
def criar_padrao(body: PadraoCreate):
    """Cria um novo padrão de detecção."""
    return repo.criar_padrao_oportunidade(nome=body.nome, expressao=body.expressao, tipo=body.tipo)


@app.post("/api/v1/padroes-oportunidade/reordenar")
def reordenar_padroes(body: PadraoReordenar):
    """Recebe lista de IDs na nova ordem e salva a prioridade."""
    return repo.reordenar_padroes_oportunidade(body.ids)


@app.put("/api/v1/padroes-oportunidade/{padrao_id}")
def atualizar_padrao(padrao_id: int, body: PadraoUpdate):
    """Atualiza nome, expressão ou status ativo de um padrão."""
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    padrao = repo.atualizar_padrao_oportunidade(padrao_id, **updates)
    if not padrao:
        raise HTTPException(status_code=404, detail="Padrão não encontrado")
    return padrao


@app.delete("/api/v1/padroes-oportunidade/{padrao_id}", status_code=204)
def deletar_padrao(padrao_id: int):
    """Remove um padrão de detecção."""
    ok = repo.deletar_padrao_oportunidade(padrao_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Padrão não encontrado")


class DescartarOportunidadeRequest(BaseModel):
    pessoa_id: int
    numero_processo: str


@app.post("/api/v1/oportunidades/descartar", status_code=201)
def descartar_oportunidade(body: DescartarOportunidadeRequest):
    """Marca um processo como descartado pelo usuário."""
    repo.descartar_oportunidade(body.pessoa_id, body.numero_processo)
    return {"status": "descartado"}


@app.delete("/api/v1/oportunidades/descartar", status_code=200)
def restaurar_oportunidade(body: DescartarOportunidadeRequest):
    """Remove o descarte de um processo (restaura para a aba original)."""
    repo.restaurar_oportunidade(body.pessoa_id, body.numero_processo)
    return {"status": "restaurado"}


@app.post("/api/v1/oportunidades/varrer")
def varrer_oportunidades(request: Request):
    """Dispara varredura imediata de oportunidades de crédito."""
    from tasks import varrer_oportunidades_task
    _tid = getattr(request.state, "tenant_id", None)
    varrer_oportunidades_task.send(_tid)
    return {"status": "varredura enfileirada"}


class ClassificarProcessoRequest(BaseModel):
    pessoa_id: int
    numero_processo: str


@app.post("/api/v1/oportunidades/classificar")
def classificar_processo_endpoint(request: Request, body: ClassificarProcessoRequest):
    """Dispara classificação IA de credor/devedor para um processo específico."""
    if not config.openai_habilitado:
        raise HTTPException(status_code=503, detail="OpenAI não configurada.")
    from tasks import classificar_processo_task
    _tid = getattr(request.state, "tenant_id", "")
    classificar_processo_task.send(_tid, body.pessoa_id, body.numero_processo)
    return {"status": "classificação enfileirada"}


class ResumoProcessoRequest(BaseModel):
    pessoa_id: int
    numero_processo: str


_RESUMO_CACHE_TTL = 60 * 60 * 24 * 7  # 7 dias


_RESUMO_CACHE_VERSION = "v3"  # v3: prompt neutro (sem viés devedor)


def _resumo_cache_key(pessoa_id: int, numero_processo: str, total_pubs: int) -> str:
    return f"resumo:{_RESUMO_CACHE_VERSION}:{pessoa_id}:{numero_processo}:{total_pubs}"


@app.post("/api/v1/oportunidades/resumo")
def resumir_processo(body: ResumoProcessoRequest):
    """Gera resumo de um processo via OpenAI a partir das publicações monitoradas.

    O resultado é cacheado no Redis por 7 dias (ou enquanto o número de publicações
    não mudar), evitando chamadas repetidas à API da OpenAI.
    """
    if not config.openai_habilitado:
        raise HTTPException(
            status_code=503,
            detail="OpenAI não configurada. Defina DJE_OPENAI_API_KEY no ambiente.",
        )

    pessoa = repo.obter_pessoa(body.pessoa_id)
    pessoa_nome = pessoa["nome"] if pessoa else None

    publicacoes = repo.buscar_publicacoes_processo(
        pessoa_id=body.pessoa_id,
        numero_processo=body.numero_processo,
    )
    if not publicacoes:
        raise HTTPException(status_code=404, detail="Nenhuma publicação encontrada para este processo.")

    import json as _json
    cache_key = _resumo_cache_key(body.pessoa_id, body.numero_processo, len(publicacoes))
    try:
        import redis as _redis
        r = _redis.from_url(config.redis_url, decode_responses=True)
        cached = r.get(cache_key)
        if cached:
            resultado = _json.loads(cached)
            resultado["cache"] = True
            return resultado
    except Exception as e:
        logger.warning(f"Redis indisponível para cache de resumo: {e}")
        r = None

    from services.resumo_service import gerar_resumo_processo
    try:
        resultado = gerar_resumo_processo(
            publicacoes=publicacoes,
            api_key=config.openai_api_key,
            modelo=config.openai_model,
            pessoa_nome=pessoa_nome,
            numero_processo=body.numero_processo,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    try:
        if r:
            r.setex(cache_key, _RESUMO_CACHE_TTL, _json.dumps(resultado, ensure_ascii=False))
    except Exception as e:
        logger.warning(f"Falha ao salvar resumo no Redis: {e}")

    resultado["cache"] = False
    return resultado


@app.post("/api/v1/search/reindex")
def trigger_reindex(request: Request):
    """Dispara reindexação completa das publicações no Qdrant."""
    from tasks import reindexar_tudo_task
    _tid = getattr(request.state, "tenant_id", None)
    reindexar_tudo_task.send(_tid)
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
