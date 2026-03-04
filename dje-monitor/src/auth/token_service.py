"""Geração e validação de JWT access tokens e refresh tokens."""

import uuid
from datetime import datetime, timedelta, timezone
from hashlib import sha256

import jwt


class TokenService:
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_expire_minutes: int = 30,
        refresh_expire_days: int = 30,
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_expire_minutes = access_expire_minutes
        self.refresh_expire_days = refresh_expire_days

    def create_access_token(self, user_id: str, tenant_id: str, role: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "tid": tenant_id,
            "role": role,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=self.access_expire_minutes),
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(
        self, user_id: str, family_id: str | None = None
    ) -> tuple[str, str, str]:
        """Retorna (token_plain, token_hash, family_id). Apenas o hash deve ser armazenado."""
        fid = family_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "fid": fid,
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=self.refresh_expire_days),
            "jti": str(uuid.uuid4()),
        }
        token_plain = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        token_hash = sha256(token_plain.encode()).hexdigest()
        return token_plain, token_hash, fid

    def decode_token(self, token: str) -> dict:
        """Decodifica e valida o token. Levanta jwt.InvalidTokenError se inválido/expirado."""
        return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

    @property
    def access_expire_seconds(self) -> int:
        return self.access_expire_minutes * 60

    @property
    def refresh_expire_datetime(self):
        return datetime.now(timezone.utc) + timedelta(days=self.refresh_expire_days)
