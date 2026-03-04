"""
Middleware de identificação e validação de tenant.

Suporta 3 modos de identificação (em ordem de prioridade):
1. Header X-Tenant-ID
2. Subdomain (ex: armando.monitor.exemplo.com)
3. Query param ?tenant= (apenas em development)

Rotas públicas (não exigem tenant):
- /health
- /docs, /openapi.json, /redoc
- /admin/* (validadas por X-Admin-Key separadamente)
"""

import logging
import os
from typing import Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from db.tenant_context import set_current_tenant, clear_current_tenant

logger = logging.getLogger(__name__)

PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}
ADMIN_PREFIX = "/admin"
AUTH_PREFIX = "/auth"  # Autenticação própria — não precisa de tenant prévio
ENVIRONMENT = os.getenv("DJE_ENVIRONMENT", "production")


class TenantMiddleware(BaseHTTPMiddleware):
    """Identifica e valida o tenant em cada request."""

    def __init__(self, app: ASGIApp, get_session_fn=None, token_service=None):
        super().__init__(app)
        self._get_session = get_session_fn
        self._token_service = token_service

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Rotas públicas — sem tenant necessário
        if path in PUBLIC_PATHS or path.startswith(ADMIN_PREFIX) or path.startswith(AUTH_PREFIX):
            clear_current_tenant()
            return await call_next(request)

        tenant_id = await self._resolve_tenant_id(request)

        if not tenant_id:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": "Tenant não identificado. Envie o header X-Tenant-ID."
                },
            )

        # Validar que o tenant existe e está ativo
        tenant = self._load_tenant(tenant_id)
        if not tenant:
            return JSONResponse(
                status_code=403,
                content={"detail": "Tenant inativo ou inexistente."},
            )

        set_current_tenant(str(tenant.id))
        request.state.tenant = tenant
        request.state.tenant_id = str(tenant.id)

        return await call_next(request)

    async def _resolve_tenant_id(self, request: Request) -> Optional[str]:
        # 0. Bearer JWT — extrai tid claim (token já será validado pelo dependency)
        if self._token_service:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                try:
                    payload = self._token_service.decode_token(auth_header[7:])
                    if payload.get("type") == "access" and payload.get("tid"):
                        return payload["tid"]
                except Exception:
                    pass  # Token inválido/expirado — deixa cair no 400 normalmente

        # 1. Header explícito
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return tenant_id.strip()

        # 2. Subdomain (ex: armando.monitor.exemplo.com)
        host = request.headers.get("host", "")
        parts = host.split(".")
        if len(parts) >= 3:
            # Verificar se o primeiro segmento é um slug conhecido
            slug = parts[0]
            tenant = self._load_tenant_by_slug(slug)
            if tenant:
                return str(tenant.id)

        # 3. Query param (apenas em development)
        if ENVIRONMENT == "development":
            return request.query_params.get("tenant")

        return None

    def _load_tenant(self, tenant_id: str):
        """Carrega tenant do banco usando a sessão disponível."""
        try:
            from services.tenant_service import TenantService, _tenant_cache
            # Fast path: verificar cache antes de abrir sessão
            if tenant_id in _tenant_cache:
                cached = _tenant_cache[tenant_id]
                return cached if cached.is_active else None

            if self._get_session:
                with self._get_session() as session:
                    svc = TenantService(session)
                    return svc.get_active_tenant(tenant_id)
        except Exception as e:
            logger.error(f"Erro ao carregar tenant {tenant_id}: {e}")
        return None

    def _load_tenant_by_slug(self, slug: str):
        """Carrega tenant pelo slug."""
        try:
            from services.tenant_service import TenantService, _slug_cache
            if slug in _slug_cache:
                cached = _slug_cache[slug]
                return cached if cached.is_active else None

            if self._get_session:
                with self._get_session() as session:
                    svc = TenantService(session)
                    return svc.get_by_slug(slug)
        except Exception as e:
            logger.error(f"Erro ao carregar tenant por slug {slug}: {e}")
        return None
