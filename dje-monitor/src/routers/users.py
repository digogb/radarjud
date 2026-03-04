"""
Router de gestão de usuários pelo admin/owner do tenant.

Todos os endpoints requerem autenticação e permissão USERS_MANAGE.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from auth.dependencies import CurrentUser, get_current_user, require_permission
from auth.permissions import Permission
from auth.role_hierarchy import VALID_ROLES, validate_role_hierarchy

logger = logging.getLogger(__name__)

router = APIRouter(tags=["users"])

# Injetado pelo api.py
_user_service = None


def set_user_service(user_service):
    global _user_service
    _user_service = user_service


def get_user_service():
    if _user_service is None:
        raise RuntimeError("UserService não inicializado.")
    return _user_service


class CreateUserRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=255)
    role: str = Field(..., description="owner|admin|advogado|estagiario|leitura")


class ChangeRoleRequest(BaseModel):
    new_role: str


@router.get("/")
def list_users(
    user: CurrentUser = Depends(require_permission(Permission.USERS_MANAGE)),
):
    """Lista todos os usuários do tenant. Requer admin ou owner."""
    svc = get_user_service()
    return svc.list_by_tenant(user.tenant_id)


@router.post("/", status_code=201)
def create_user(
    data: CreateUserRequest,
    user: CurrentUser = Depends(require_permission(Permission.USERS_MANAGE)),
):
    """
    Admin cria conta para membro da equipe.
    Retorna senha temporária — mostrar apenas uma vez.
    """
    svc = get_user_service()
    result = svc.create(
        tenant_id=user.tenant_id,
        email=data.email,
        name=data.name,
        role=data.role,
        created_by=user.user_id,
        actor_role=user.role,
    )
    return result


@router.get("/{user_id}")
def get_user(
    user_id: str,
    user: CurrentUser = Depends(require_permission(Permission.USERS_MANAGE)),
):
    """Retorna dados de um usuário do tenant."""
    svc = get_user_service()
    target = svc.get_by_id(user_id, user.tenant_id)
    if not target:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return target


@router.patch("/{user_id}/role")
def change_role(
    user_id: str,
    data: ChangeRoleRequest,
    user: CurrentUser = Depends(require_permission(Permission.USERS_ROLES)),
):
    """Altera role de um usuário. Respeita hierarquia."""
    if user_id == user.user_id:
        raise HTTPException(status_code=400, detail="Você não pode alterar seu próprio role.")
    svc = get_user_service()
    return svc.change_role(
        user_id=user_id,
        new_role=data.new_role,
        changed_by=user.user_id,
        actor_role=user.role,
        tenant_id=user.tenant_id,
    )


@router.post("/{user_id}/deactivate")
def deactivate_user(
    user_id: str,
    user: CurrentUser = Depends(require_permission(Permission.USERS_MANAGE)),
):
    """Desativa usuário (soft delete). Revoga todos os tokens."""
    if user_id == user.user_id:
        raise HTTPException(status_code=400, detail="Você não pode desativar a si mesmo.")
    svc = get_user_service()
    svc.deactivate(user_id, deactivated_by=user.user_id, tenant_id=user.tenant_id)
    return {"message": "Usuário desativado"}


@router.post("/{user_id}/reset-password")
def admin_reset_password(
    user_id: str,
    user: CurrentUser = Depends(require_permission(Permission.USERS_MANAGE)),
):
    """Admin reseta a senha de um usuário. Gera nova senha temporária (exibida apenas uma vez)."""
    svc = get_user_service()
    temp_password = svc.reset_password(user_id, reset_by=user.user_id, tenant_id=user.tenant_id)
    return {"temporary_password": temp_password}


@router.get("/audit-log/recent")
def get_audit_log(
    limit: int = 100,
    user: CurrentUser = Depends(require_permission(Permission.AUDIT_VIEW)),
):
    """Lista audit log do tenant. Requer admin ou owner."""
    svc = get_user_service()
    return svc.get_audit_log(user.tenant_id, limit=limit)
