"""
Serviço de autenticação: login, refresh token rotation e logout.

Todas as operações são síncronas (SQLAlchemy sync + psycopg2).
"""

import json
import logging
from datetime import datetime, timezone
from hashlib import sha256

import jwt

from auth.password import hash_password, verify_password
from auth.token_service import TokenService
from storage.models import User, RefreshToken, AuthAuditLog, Tenant

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    pass


class AccountLockedError(AuthenticationError):
    pass


class AuthService:
    def __init__(self, session_factory, token_service: TokenService, max_login_attempts: int = 5, lockout_minutes: int = 15):
        self._session_factory = session_factory
        self.tokens = token_service
        self.max_login_attempts = max_login_attempts
        self.lockout_minutes = lockout_minutes

    def _get_admin_session(self):
        """Sessão sem RLS (sem SET LOCAL app.current_tenant) — para operações de admin."""
        return self._session_factory(tenant_id=None)

    def login(self, email: str, password: str, ip: str, user_agent: str) -> dict:
        with self._get_admin_session() as session:
            # Busca por email sem RLS (pode estar em qualquer tenant)
            user = (
                session.query(User)
                .filter(User.email == email)
                .first()
            )

            if not user:
                # Timing attack: simular verificação para manter tempo constante
                verify_password("dummy_timing_protection", hash_password("dummy"))
                raise AuthenticationError("Credenciais inválidas")

            # Verificar lockout
            now = datetime.now(timezone.utc)
            if user.locked_until:
                locked_until_aware = user.locked_until.replace(tzinfo=timezone.utc) if user.locked_until.tzinfo is None else user.locked_until
                if locked_until_aware > now:
                    self._log_audit(session, user.tenant_id, user.id, "login_blocked", ip, user_agent)
                    session.commit()
                    remaining = int((locked_until_aware - now).total_seconds() // 60)
                    raise AccountLockedError(f"Conta bloqueada. Tente novamente em {remaining} minutos.")

            # Verificar senha
            if not verify_password(password, user.password_hash):
                self._handle_failed_login(session, user, ip, user_agent)
                raise AuthenticationError("Credenciais inválidas")

            # Verificar tenant ativo
            tenant = session.query(Tenant).filter(Tenant.id == user.tenant_id).first()
            if not tenant or not tenant.is_active:
                raise AuthenticationError("Escritório desativado. Contate o suporte.")

            # Verificar usuário ativo
            if not user.is_active:
                raise AuthenticationError("Conta desativada. Contate o administrador.")

            # Gerar tokens
            access_token = self.tokens.create_access_token(
                str(user.id), str(user.tenant_id), user.role
            )
            refresh_plain, refresh_hash, family_id = self.tokens.create_refresh_token(str(user.id))

            # Salvar refresh token
            rt = RefreshToken(
                user_id=user.id,
                token_hash=refresh_hash,
                family_id=family_id,
                expires_at=self.tokens.refresh_expire_datetime,
            )
            session.add(rt)

            # Reset tentativas + registrar login
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_login_at = datetime.utcnow()
            self._log_audit(session, user.tenant_id, user.id, "login", ip, user_agent)
            session.commit()

            return {
                "access_token": access_token,
                "refresh_token": refresh_plain,
                "token_type": "bearer",
                "expires_in": self.tokens.access_expire_seconds,
                "user": {
                    "id": str(user.id),
                    "name": user.name,
                    "email": user.email,
                    "role": user.role,
                    "tenant_id": str(user.tenant_id),
                    "tenant_name": tenant.name,
                    "must_change_password": user.must_change_password,
                },
            }

    def refresh(self, refresh_token: str) -> dict:
        """Refresh Token Rotation — cada token só pode ser usado UMA vez."""
        try:
            payload = self.tokens.decode_token(refresh_token)
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Refresh token expirado. Faça login novamente.")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Token inválido.")

        if payload.get("type") != "refresh":
            raise AuthenticationError("Token inválido.")

        token_hash = sha256(refresh_token.encode()).hexdigest()
        family_id = payload["fid"]
        user_id = payload["sub"]

        with self._get_admin_session() as session:
            stored = (
                session.query(RefreshToken)
                .filter(RefreshToken.token_hash == token_hash)
                .first()
            )

            if not stored:
                # Token não encontrado — possível reuso de token antigo (ataque)
                self._revoke_token_family(session, family_id)
                session.commit()
                raise AuthenticationError("Token inválido. Sessões revogadas por segurança.")

            if stored.is_revoked:
                # Reuso detectado — revogar toda a família
                self._revoke_token_family(session, family_id)
                session.commit()
                raise AuthenticationError("Reuso de token detectado. Faça login novamente.")

            # Revogar o token atual
            stored.is_revoked = True

            # Buscar usuário
            user = session.query(User).filter(User.id == user_id).first()
            if not user or not user.is_active:
                session.commit()
                raise AuthenticationError("Conta não encontrada ou desativada.")

            # Gerar novos tokens (mesma family)
            access_token = self.tokens.create_access_token(
                str(user.id), str(user.tenant_id), user.role
            )
            new_refresh_plain, new_refresh_hash, _ = self.tokens.create_refresh_token(
                str(user.id), family_id=family_id
            )

            # Novo refresh token
            new_rt = RefreshToken(
                user_id=user.id,
                token_hash=new_refresh_hash,
                family_id=family_id,
                expires_at=self.tokens.refresh_expire_datetime,
                replaced_by=None,
            )
            session.add(new_rt)
            session.flush()

            # Rastrear substituição
            stored.replaced_by = new_rt.id
            session.commit()

            return {
                "access_token": access_token,
                "refresh_token": new_refresh_plain,
                "token_type": "bearer",
                "expires_in": self.tokens.access_expire_seconds,
            }

    def logout(self, refresh_token: str) -> None:
        """Revoga a family inteira do refresh token (logout de todas as sessões)."""
        try:
            payload = self.tokens.decode_token(refresh_token)
            family_id = payload.get("fid")
            if family_id:
                with self._get_admin_session() as session:
                    self._revoke_token_family(session, family_id)
                    session.commit()
        except jwt.InvalidTokenError:
            pass  # Token inválido, nada a revogar

    def revoke_all_user_tokens(self, user_id: str) -> None:
        """Revoga todos os refresh tokens de um usuário (ex: ao desativar conta ou resetar senha)."""
        with self._get_admin_session() as session:
            tokens = session.query(RefreshToken).filter(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked == False,
            ).all()
            for t in tokens:
                t.is_revoked = True
            session.commit()

    def change_password(self, user_id: str, current_password: str, new_password: str) -> None:
        with self._get_admin_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                raise AuthenticationError("Usuário não encontrado.")
            if not verify_password(current_password, user.password_hash):
                raise AuthenticationError("Senha atual incorreta.")
            user.password_hash = hash_password(new_password)
            user.password_changed_at = datetime.utcnow()
            user.must_change_password = False
            # Revogar todos os refresh tokens (forçar re-login)
            self._revoke_all_user_tokens_in_session(session, user_id)
            session.commit()

    def _handle_failed_login(self, session, user: User, ip: str, user_agent: str) -> None:
        from datetime import timedelta
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= self.max_login_attempts:
            user.locked_until = datetime.utcnow() + timedelta(minutes=self.lockout_minutes)
        self._log_audit(session, user.tenant_id, user.id, "login_failed", ip, user_agent)
        session.commit()

    def _revoke_token_family(self, session, family_id: str) -> None:
        tokens = session.query(RefreshToken).filter(
            RefreshToken.family_id == family_id,
            RefreshToken.is_revoked == False,
        ).all()
        for t in tokens:
            t.is_revoked = True

    def _revoke_all_user_tokens_in_session(self, session, user_id: str) -> None:
        tokens = session.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False,
        ).all()
        for t in tokens:
            t.is_revoked = True

    def _log_audit(self, session, tenant_id: str, user_id: str | None, action: str, ip: str, user_agent: str, details: dict | None = None) -> None:
        log = AuthAuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            ip_address=ip,
            user_agent=user_agent,
            details=details or {},
        )
        session.add(log)
