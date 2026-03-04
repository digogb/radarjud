"""
FastAPI dependencies para autenticação e autorização.

Uso nos endpoints:
    user: CurrentUser = Depends(get_current_user)
    user: CurrentUser = Depends(require_permission(Permission.PROCESSOS_DELETE))
"""

import logging

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth.permissions import Permission, has_permission
from db.tenant_context import set_current_tenant

logger = logging.getLogger(__name__)

security = HTTPBearer()

# Injetado pelo api.py após inicialização
_token_service = None


def set_token_service(token_service):
    global _token_service
    _token_service = token_service


def get_token_service():
    if _token_service is None:
        raise RuntimeError("TokenService não inicializado. Configure DJE_AUTH_JWT_SECRET.")
    return _token_service


class CurrentUser:
    """Dados do usuário autenticado extraídos do JWT."""

    def __init__(self, user_id: str, tenant_id: str, role: str):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role

    def can(self, permission: Permission) -> bool:
        return has_permission(self.role, permission)

    def require(self, permission: Permission):
        if not self.can(permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permissão negada: {permission.value}",
            )

    def __repr__(self):
        return f"<CurrentUser(id='{self.user_id}', role='{self.role}')>"


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    token_service = get_token_service()
    try:
        payload = token_service.decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Token inválido")

    user = CurrentUser(
        user_id=payload["sub"],
        tenant_id=payload["tid"],
        role=payload["role"],
    )

    # Setar tenant a partir do JWT (substitui o X-Tenant-ID header)
    set_current_tenant(user.tenant_id)

    return user


def require_permission(permission: Permission):
    """Dependency factory para proteger endpoints por permissão."""
    def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        user.require(permission)
        return user
    return _check


# Atalhos comuns
def require_owner(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    user.require(Permission.TENANT_SETTINGS)
    return user


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    user.require(Permission.USERS_MANAGE)
    return user
