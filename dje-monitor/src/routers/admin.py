"""
API Admin para gerenciamento de Tenants.

Autenticação: header X-Admin-Key validado contra DJE_ADMIN_KEY env var.
Rotas prefixadas em /admin/tenants/ — não passam pelo TenantMiddleware.
"""

import logging
import os

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from schemas.tenant import TenantCreate, TenantUpdate, TenantResponse, TenantWithStats
from services.tenant_service import TenantService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/tenants", tags=["admin"])

ADMIN_KEY = os.getenv("DJE_ADMIN_KEY", "")


def _require_admin(x_admin_key: str = Header(..., alias="X-Admin-Key")):
    """Dependency que valida a chave de admin."""
    if not ADMIN_KEY:
        raise HTTPException(
            status_code=503,
            detail="Admin não configurado. Defina DJE_ADMIN_KEY no ambiente.",
        )
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Chave de admin inválida.")


# Injetado pela api.py ao registrar o router
_get_session_fn = None


def _get_session() -> Session:
    if _get_session_fn is None:
        raise RuntimeError("_get_session_fn não configurado no router admin")
    return _get_session_fn()


@router.post("/", status_code=201, dependencies=[Depends(_require_admin)])
def create_tenant(data: TenantCreate):
    """Cria tenant + collections no Qdrant + setup inicial."""
    with _get_session() as session:
        svc = TenantService(session)
        # Checar slug duplicado
        existing = svc.get_by_slug(data.slug)
        if existing:
            raise HTTPException(status_code=409, detail=f"Slug '{data.slug}' já existe.")
        tenant = svc.create_tenant(name=data.name, slug=data.slug, settings=data.settings)

    # Criar collections no Qdrant
    try:
        from services.qdrant_tenant import ensure_tenant_collections
        ensure_tenant_collections(tenant.id)
    except Exception as e:
        logger.warning(f"Não foi possível criar collections Qdrant para tenant {tenant.id}: {e}")

    return TenantResponse.from_orm(tenant)


@router.get("/", dependencies=[Depends(_require_admin)])
def list_tenants():
    """Lista todos os tenants com stats básicas."""
    with _get_session() as session:
        svc = TenantService(session)
        tenants = svc.list_all()
        result = []
        for t in tenants:
            stats = svc.get_stats(t.id)
            tw = TenantWithStats(
                **TenantResponse.from_orm(t).model_dump(),
                total_pessoas=stats["total_pessoas"],
                total_publicacoes=stats["total_publicacoes"],
                total_alertas_nao_lidos=stats["total_alertas_nao_lidos"],
            )
            result.append(tw)
    return result


@router.get("/{tenant_id}/stats", dependencies=[Depends(_require_admin)])
def tenant_stats(tenant_id: str):
    """Stats do tenant: pessoas monitoradas, publicações, alertas não lidos."""
    with _get_session() as session:
        svc = TenantService(session)
        tenant = session.get_session if False else svc.get_active_tenant(tenant_id)
        if not tenant:
            # Tentar mesmo que inativo (admin pode querer ver stats de inativo)
            from storage.models import Tenant
            tenant = session.get(Tenant, tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant não encontrado.")
        return svc.get_stats(tenant_id)


@router.patch("/{tenant_id}", dependencies=[Depends(_require_admin)])
def update_tenant(tenant_id: str, data: TenantUpdate):
    """Atualiza nome, settings ou status de um tenant."""
    with _get_session() as session:
        svc = TenantService(session)
        updates = {k: v for k, v in data.model_dump().items() if v is not None}
        tenant = svc.update_tenant(tenant_id, **updates)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant não encontrado.")
        return TenantResponse.from_orm(tenant)


@router.post("/{tenant_id}/deactivate", dependencies=[Depends(_require_admin)])
def deactivate_tenant(tenant_id: str):
    """Desativa tenant (soft delete — dados mantidos)."""
    with _get_session() as session:
        svc = TenantService(session)
        tenant = svc.deactivate_tenant(tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant não encontrado.")
        return {"status": "desativado", "tenant_id": tenant_id}


@router.delete("/{tenant_id}", dependencies=[Depends(_require_admin)])
def delete_tenant(tenant_id: str, confirmar: bool = False):
    """
    HARD DELETE — Remove tenant completamente.

    Remove: collection Qdrant + keys Redis + dados PostgreSQL.
    Requer query param ?confirmar=true para evitar acidentes.
    """
    if not confirmar:
        raise HTTPException(
            status_code=400,
            detail="Passe ?confirmar=true para confirmar a exclusão permanente.",
        )

    # 1. Remover collections Qdrant
    try:
        from services.qdrant_tenant import delete_tenant_collections
        delete_tenant_collections(tenant_id)
    except Exception as e:
        logger.warning(f"Erro ao remover collections Qdrant do tenant {tenant_id}: {e}")

    # 2. Remover cache Redis
    try:
        from cache.tenant_cache import TenantCache
        import redis
        from config import Config
        cfg = Config()
        r = redis.from_url(cfg.redis_url)
        TenantCache(r).delete_tenant_data(tenant_id)
    except Exception as e:
        logger.warning(f"Erro ao limpar Redis do tenant {tenant_id}: {e}")

    # 3. Remover do banco
    with _get_session() as session:
        svc = TenantService(session)
        ok = svc.hard_delete(tenant_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Tenant não encontrado.")

    return {"status": "deleted", "tenant_id": tenant_id}
