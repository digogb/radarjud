"""
Cache Redis com isolamento por tenant.

Todas as keys são prefixadas com t:{tenant_id}: para garantir que
um tenant não acesse dados de outro tenant via cache.
"""

import logging
import redis

logger = logging.getLogger(__name__)


class TenantCache:
    """Cache Redis com namespace por tenant."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def _key(self, tenant_id: str, key: str) -> str:
        """Gera key Redis namespaced com tenant_id."""
        return f"t:{tenant_id}:{key}"

    def get(self, tenant_id: str, key: str) -> str | None:
        """Retorna valor do cache ou None se não encontrado."""
        try:
            value = self.redis.get(self._key(tenant_id, key))
            return value.decode() if isinstance(value, bytes) else value
        except Exception as e:
            logger.warning(f"TenantCache.get erro: {e}")
            return None

    def set(self, tenant_id: str, key: str, value: str, ttl: int = 3600) -> bool:
        """Armazena valor no cache com TTL em segundos."""
        try:
            self.redis.set(self._key(tenant_id, key), value, ex=ttl)
            return True
        except Exception as e:
            logger.warning(f"TenantCache.set erro: {e}")
            return False

    def delete(self, tenant_id: str, key: str) -> bool:
        """Remove uma key do cache."""
        try:
            self.redis.delete(self._key(tenant_id, key))
            return True
        except Exception as e:
            logger.warning(f"TenantCache.delete erro: {e}")
            return False

    def delete_tenant_data(self, tenant_id: str) -> int:
        """Remove TODAS as keys do tenant. Usar durante hard delete."""
        pattern = f"t:{tenant_id}:*"
        deleted = 0
        try:
            for key in self.redis.scan_iter(match=pattern, count=100):
                self.redis.delete(key)
                deleted += 1
            logger.warning(f"TenantCache: {deleted} keys removidas para tenant {tenant_id}")
        except Exception as e:
            logger.error(f"TenantCache.delete_tenant_data erro: {e}")
        return deleted
