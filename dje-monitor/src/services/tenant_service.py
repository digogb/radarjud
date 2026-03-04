"""
Serviço de gerenciamento de Tenants.

Responsável por:
- CRUD de tenants
- Cache em memória para lookups rápidos (evita hit no banco a cada request)
- Stats por tenant
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from storage.models import (
    Tenant,
    PessoaMonitorada,
    PublicacaoMonitorada,
    Alerta,
)

logger = logging.getLogger(__name__)

# Cache em memória: tenant_id → Tenant
# TTL simples: invalidado quando tenant é atualizado/criado
_tenant_cache: dict[str, Tenant] = {}
_slug_cache: dict[str, Tenant] = {}


def _cache_tenant(tenant: Tenant) -> None:
    _tenant_cache[tenant.id] = tenant
    _slug_cache[tenant.slug] = tenant


def invalidate_tenant_cache(tenant_id: str | None = None) -> None:
    """Invalida cache (total ou para um tenant específico)."""
    global _tenant_cache, _slug_cache
    if tenant_id is None:
        _tenant_cache.clear()
        _slug_cache.clear()
    else:
        tenant = _tenant_cache.pop(tenant_id, None)
        if tenant:
            _slug_cache.pop(tenant.slug, None)


class TenantService:
    """CRUD e queries de tenant. Requer uma Session do SQLAlchemy."""

    def __init__(self, session: Session):
        self.session = session

    def get_active_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Retorna tenant ativo pelo ID. Usa cache em memória."""
        if tenant_id in _tenant_cache:
            tenant = _tenant_cache[tenant_id]
            return tenant if tenant.is_active else None

        tenant = self.session.get(Tenant, tenant_id)
        if tenant:
            _cache_tenant(tenant)
        return tenant if tenant and tenant.is_active else None

    def get_by_slug(self, slug: str) -> Optional[Tenant]:
        """Retorna tenant ativo pelo slug. Usa cache em memória."""
        if slug in _slug_cache:
            tenant = _slug_cache[slug]
            return tenant if tenant.is_active else None

        tenant = self.session.execute(
            select(Tenant).where(Tenant.slug == slug, Tenant.is_active == True)
        ).scalar_one_or_none()
        if tenant:
            _cache_tenant(tenant)
        return tenant

    def create_tenant(self, name: str, slug: str, settings: dict | None = None) -> Tenant:
        """Cria um novo tenant."""
        tenant = Tenant(name=name, slug=slug, settings=settings or {})
        self.session.add(tenant)
        self.session.commit()
        self.session.refresh(tenant)
        _cache_tenant(tenant)
        logger.info(f"Tenant criado: {tenant.slug} ({tenant.id})")
        return tenant

    def update_tenant(self, tenant_id: str, **kwargs) -> Optional[Tenant]:
        """Atualiza campos de um tenant."""
        tenant = self.session.get(Tenant, tenant_id)
        if not tenant:
            return None
        for key, value in kwargs.items():
            if hasattr(tenant, key) and value is not None:
                setattr(tenant, key, value)
        tenant.updated_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(tenant)
        invalidate_tenant_cache(tenant_id)
        _cache_tenant(tenant)
        return tenant

    def deactivate_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Desativa um tenant (soft delete — dados mantidos)."""
        return self.update_tenant(tenant_id, is_active=False)

    def list_all(self) -> list[Tenant]:
        """Lista todos os tenants (ativo ou não)."""
        return list(self.session.execute(
            select(Tenant).order_by(Tenant.created_at)
        ).scalars().all())

    def hard_delete(self, tenant_id: str) -> bool:
        """Remove tenant do banco. Dados devem ser removidos antes (Qdrant, Redis, tabelas)."""
        tenant = self.session.get(Tenant, tenant_id)
        if not tenant:
            return False
        self.session.delete(tenant)
        self.session.commit()
        invalidate_tenant_cache(tenant_id)
        logger.warning(f"Tenant hard-deleted: {tenant_id}")
        return True

    def get_stats(self, tenant_id: str) -> dict:
        """Retorna estatísticas básicas do tenant."""
        total_pessoas = self.session.scalar(
            select(func.count(PessoaMonitorada.id)).where(
                PessoaMonitorada.tenant_id == tenant_id,
                PessoaMonitorada.ativo == True,
            )
        ) or 0

        total_publicacoes = self.session.scalar(
            select(func.count(PublicacaoMonitorada.id)).where(
                PublicacaoMonitorada.tenant_id == tenant_id
            )
        ) or 0

        total_alertas_nao_lidos = self.session.scalar(
            select(func.count(Alerta.id)).where(
                Alerta.tenant_id == tenant_id,
                Alerta.lido == False,
            )
        ) or 0

        return {
            "tenant_id": tenant_id,
            "total_pessoas": total_pessoas,
            "total_publicacoes": total_publicacoes,
            "total_alertas_nao_lidos": total_alertas_nao_lidos,
        }
