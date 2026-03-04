"""
Rate limiting por IP para o endpoint de login.

Complementa o lockout por conta (que é por usuário, implementado no AuthService).
"""

import logging

import redis as redis_lib
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class LoginRateLimiter:
    """Rate limiting por IP no endpoint /auth/login."""

    def __init__(self, redis_url: str, max_attempts: int = 20, window_seconds: int = 900):
        self._redis_url = redis_url
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = redis_lib.from_url(self._redis_url, decode_responses=True)
        return self._client

    def check(self, ip: str) -> None:
        """Levanta HTTPException 429 se o IP excedeu o limite de tentativas."""
        try:
            r = self._get_client()
            key = f"login_rate:{ip}"
            attempts = r.incr(key)
            if attempts == 1:
                r.expire(key, self.window_seconds)
            if attempts > self.max_attempts:
                raise HTTPException(
                    status_code=429,
                    detail=f"Muitas tentativas de login. Tente novamente em {self.window_seconds // 60} minutos.",
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Rate limiter indisponível: {e}")
            # Não bloquear se Redis estiver down
