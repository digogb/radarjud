"""
Serviço de gestão de usuários por admin/owner do tenant.
"""

import logging
import secrets
import string
import uuid
from datetime import datetime

from fastapi import HTTPException

from auth.password import hash_password
from auth.role_hierarchy import VALID_ROLES, validate_role_hierarchy
from storage.models import User, RefreshToken, AuthAuditLog

logger = logging.getLogger(__name__)


def _generate_temp_password(length: int = 12) -> str:
    """Gera uma senha temporária segura."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


class UserService:
    def __init__(self, session_factory):
        self._session_factory = session_factory

    def _get_session(self, tenant_id: str | None = None):
        return self._session_factory(tenant_id=tenant_id)

    def list_by_tenant(self, tenant_id: str) -> list[dict]:
        with self._get_session(tenant_id) as session:
            users = (
                session.query(User)
                .filter(User.tenant_id == tenant_id)
                .order_by(User.created_at)
                .all()
            )
            return [_user_to_dict(u) for u in users]

    def get_by_id(self, user_id: str, tenant_id: str) -> dict | None:
        with self._get_session(tenant_id) as session:
            user = session.query(User).filter(
                User.id == user_id,
                User.tenant_id == tenant_id,
            ).first()
            return _user_to_dict(user) if user else None

    def create(
        self,
        tenant_id: str,
        email: str,
        name: str,
        role: str,
        created_by: str,
        actor_role: str,
    ) -> dict:
        if role not in VALID_ROLES:
            raise HTTPException(status_code=400, detail=f"Role inválido: {role}")
        validate_role_hierarchy(actor_role, role)

        temp_password = _generate_temp_password()

        with self._get_session(tenant_id) as session:
            # Verificar se email já existe no tenant
            existing = session.query(User).filter(
                User.tenant_id == tenant_id,
                User.email == email,
            ).first()
            if existing:
                raise HTTPException(status_code=409, detail="Email já cadastrado neste tenant.")

            user = User(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                email=email,
                name=name,
                role=role,
                password_hash=hash_password(temp_password),
                is_active=True,
                must_change_password=True,
                created_by=created_by,
            )
            session.add(user)

            # Audit log
            log = AuthAuditLog(
                tenant_id=tenant_id,
                user_id=created_by,
                action="user_created",
                details={"new_user_email": email, "role": role},
            )
            session.add(log)
            session.commit()
            session.refresh(user)

            result = _user_to_dict(user)
            result["temporary_password"] = temp_password  # Apenas retornado uma vez
            return result

    def change_role(
        self,
        user_id: str,
        new_role: str,
        changed_by: str,
        actor_role: str,
        tenant_id: str,
    ) -> dict:
        if new_role not in VALID_ROLES:
            raise HTTPException(status_code=400, detail=f"Role inválido: {new_role}")
        validate_role_hierarchy(actor_role, new_role)

        with self._get_session(tenant_id) as session:
            user = session.query(User).filter(
                User.id == user_id,
                User.tenant_id == tenant_id,
            ).first()
            if not user:
                raise HTTPException(status_code=404, detail="Usuário não encontrado.")

            # Verificar hierarquia sobre o role atual do usuário
            validate_role_hierarchy(actor_role, user.role)

            old_role = user.role
            user.role = new_role
            user.updated_at = datetime.utcnow()

            log = AuthAuditLog(
                tenant_id=tenant_id,
                user_id=changed_by,
                action="role_changed",
                details={"target_user": user_id, "old_role": old_role, "new_role": new_role},
            )
            session.add(log)
            session.commit()
            session.refresh(user)
            return _user_to_dict(user)

    def deactivate(self, user_id: str, deactivated_by: str, tenant_id: str) -> None:
        with self._get_session(tenant_id) as session:
            user = session.query(User).filter(
                User.id == user_id,
                User.tenant_id == tenant_id,
            ).first()
            if not user:
                raise HTTPException(status_code=404, detail="Usuário não encontrado.")

            user.is_active = False
            user.updated_at = datetime.utcnow()

            # Revogar todos os refresh tokens
            tokens = session.query(RefreshToken).filter(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked == False,
            ).all()
            for t in tokens:
                t.is_revoked = True

            log = AuthAuditLog(
                tenant_id=tenant_id,
                user_id=deactivated_by,
                action="user_deactivated",
                details={"target_user": user_id},
            )
            session.add(log)
            session.commit()

    def reset_password(self, user_id: str, reset_by: str, tenant_id: str) -> str:
        """Admin reseta senha — retorna senha temporária (exibir apenas uma vez)."""
        temp_password = _generate_temp_password()

        with self._get_session(tenant_id) as session:
            user = session.query(User).filter(
                User.id == user_id,
                User.tenant_id == tenant_id,
            ).first()
            if not user:
                raise HTTPException(status_code=404, detail="Usuário não encontrado.")

            user.password_hash = hash_password(temp_password)
            user.must_change_password = True
            user.updated_at = datetime.utcnow()

            # Revogar todos os refresh tokens
            tokens = session.query(RefreshToken).filter(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked == False,
            ).all()
            for t in tokens:
                t.is_revoked = True

            log = AuthAuditLog(
                tenant_id=tenant_id,
                user_id=reset_by,
                action="password_reset",
                details={"target_user": user_id},
            )
            session.add(log)
            session.commit()

        return temp_password

    def get_audit_log(self, tenant_id: str, limit: int = 100) -> list[dict]:
        with self._get_session() as session:
            logs = (
                session.query(AuthAuditLog)
                .filter(AuthAuditLog.tenant_id == tenant_id)
                .order_by(AuthAuditLog.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": log.id,
                    "user_id": log.user_id,
                    "action": log.action,
                    "ip_address": log.ip_address,
                    "details": log.details,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ]


def _user_to_dict(user: User) -> dict:
    return {
        "id": str(user.id),
        "tenant_id": str(user.tenant_id),
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "is_active": user.is_active,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "must_change_password": user.must_change_password or False,
        "created_by": user.created_by,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }
