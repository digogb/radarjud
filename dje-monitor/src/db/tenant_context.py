"""
Contexto de tenant para isolamento de dados via RLS no PostgreSQL.

Usa ContextVar para propagar o tenant_id no contexto da request/task atual,
sem necessidade de passar explicitamente por toda a cadeia de chamadas.
"""

from contextvars import ContextVar
from sqlalchemy.orm import Session
from sqlalchemy import text

_current_tenant: ContextVar[str | None] = ContextVar("current_tenant", default=None)


def get_current_tenant() -> str:
    """Retorna o tenant_id do contexto atual. Lança RuntimeError se não definido."""
    tenant = _current_tenant.get()
    if not tenant:
        raise RuntimeError("Tenant não definido no contexto atual")
    return tenant


def set_current_tenant(tenant_id: str) -> None:
    """Define o tenant_id no contexto da coroutine/thread atual."""
    _current_tenant.set(tenant_id)


def clear_current_tenant() -> None:
    """Limpa o tenant do contexto (útil para admin/health routes)."""
    _current_tenant.set(None)


def get_current_tenant_or_none() -> str | None:
    """Retorna o tenant_id ou None se não definido."""
    return _current_tenant.get()


def set_tenant_on_session(session: Session, tenant_id: str) -> None:
    """
    Seta o tenant na sessão PostgreSQL para que o RLS funcione.
    Usa SET LOCAL para que a configuração seja descartada ao fechar a transação.
    """
    session.execute(
        text("SET LOCAL app.current_tenant = :tenant_id"),
        {"tenant_id": tenant_id},
    )
