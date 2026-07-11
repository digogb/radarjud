# Plano de Implementação — Autenticação e Autorização

## Visão Geral

Autenticação self-hosted com JWT + bcrypt, integrada ao sistema multi-tenant existente. O admin do escritório (tenant) gerencia os usuários da sua equipe. Cada usuário pertence a exatamente um tenant e tem um role que define o que pode fazer.

### Premissas

- Usuários são equipe interna do escritório (advogados, estagiários, admin)
- Admin do tenant cria as contas (sem self-signup)
- Login com email + senha
- JWT access token (curta duração) + refresh token (longa duração, rotativo)
- Roles: `owner`, `admin`, `advogado`, `estagiario`, `leitura`

### Fluxo de Autenticação

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Frontend  │         │   FastAPI    │         │  PostgreSQL  │
│   (React)   │         │   (Auth)     │         │  + Redis     │
└──────┬──────┘         └──────┬──────┘         └──────┬──────┘
       │                       │                       │
       │  POST /auth/login     │                       │
       │  {email, password}    │                       │
       ├──────────────────────►│                       │
       │                       │  SELECT user WHERE    │
       │                       │  email = ? AND        │
       │                       │  tenant.is_active     │
       │                       ├──────────────────────►│
       │                       │◄──────────────────────┤
       │                       │                       │
       │                       │  bcrypt.verify()      │
       │                       │  gerar access_token   │
       │                       │  gerar refresh_token  │
       │                       │                       │
       │                       │  Redis: salvar        │
       │                       │  refresh token family  │
       │                       ├──────────────────────►│
       │  {access, refresh}    │                       │
       │◄──────────────────────┤                       │
       │                       │                       │
       │  GET /api/processos   │                       │
       │  Authorization:       │                       │
       │  Bearer <access>      │                       │
       ├──────────────────────►│                       │
       │                       │  Decode JWT →         │
       │                       │  tenant_id + user_id  │
       │                       │  + role               │
       │                       │                       │
       │                       │  SET app.current_     │
       │                       │  tenant = tenant_id   │
       │                       ├──────────────────────►│
       │  { dados filtrados    │                       │
       │    por tenant + role }│                       │
       │◄──────────────────────┤                       │
```

---

## Fase 1 — Schema de Usuários e Roles (2-3 dias)

### Objetivo
Criar tabelas de users, roles e permissões no PostgreSQL, integradas com o schema de tenants.

### 1.1 — Tabela de Usuários

```sql
-- migrations/010_create_users.sql

CREATE TYPE user_role AS ENUM ('owner', 'admin', 'advogado', 'estagiario', 'leitura');

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'leitura',
    is_active BOOLEAN DEFAULT true,
    
    -- Controle de acesso
    last_login_at TIMESTAMPTZ,
    password_changed_at TIMESTAMPTZ DEFAULT now(),
    failed_login_attempts INT DEFAULT 0,
    locked_until TIMESTAMPTZ,
    
    -- Metadata
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    
    -- Email único por tenant (mesmo email pode existir em tenants diferentes)
    CONSTRAINT uq_user_email_tenant UNIQUE (tenant_id, email)
);

CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_tenant_active ON users(tenant_id, is_active) WHERE is_active = true;

-- RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_users ON users
    USING (tenant_id = current_setting('app.current_tenant')::UUID);
```

### 1.2 — Tabela de Refresh Tokens

```sql
-- migrations/011_create_refresh_tokens.sql

CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,          -- SHA-256 do token (nunca armazenar plain)
    family_id UUID NOT NULL,                    -- Para token rotation detection
    is_revoked BOOLEAN DEFAULT false,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    replaced_by UUID REFERENCES refresh_tokens(id)  -- Rastreabilidade
);

CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens(token_hash) WHERE NOT is_revoked;
CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_family ON refresh_tokens(family_id);

-- Cleanup automático de tokens expirados
CREATE INDEX idx_refresh_tokens_expired ON refresh_tokens(expires_at) WHERE NOT is_revoked;
```

### 1.3 — Tabela de Audit Log (login/logout/ações sensíveis)

```sql
-- migrations/012_create_audit_log.sql

CREATE TABLE auth_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    user_id UUID REFERENCES users(id),
    action VARCHAR(50) NOT NULL,   -- 'login', 'login_failed', 'logout', 'password_reset',
                                   -- 'user_created', 'user_deactivated', 'role_changed'
    ip_address INET,
    user_agent TEXT,
    details JSONB DEFAULT '{}',    -- Dados adicionais (ex: role anterior/novo)
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_audit_tenant_date ON auth_audit_log(tenant_id, created_at DESC);
CREATE INDEX idx_audit_user ON auth_audit_log(user_id, created_at DESC);
```

### 1.4 — Matriz de Permissões por Role

```
Permissão                    owner   admin   advogado   estagiario   leitura
─────────────────────────────────────────────────────────────────────────────
Visualizar processos          ✓       ✓        ✓           ✓           ✓
Busca semântica               ✓       ✓        ✓           ✓           ✓
Cadastrar processo            ✓       ✓        ✓           ✓           ✗
Editar processo               ✓       ✓        ✓           ✗           ✗
Excluir processo              ✓       ✓        ✗           ✗           ✗
Gerenciar usuários            ✓       ✓        ✗           ✗           ✗
Alterar roles                 ✓       ✓*       ✗           ✗           ✗
Configurações do tenant       ✓       ✗        ✗           ✗           ✗
Ver audit log                 ✓       ✓        ✗           ✗           ✗
Exportar dados                ✓       ✓        ✓           ✗           ✗

* admin pode alterar roles de advogado/estagiario/leitura, mas não de outros admins
```

```python
# app/auth/permissions.py

from enum import Enum


class Permission(str, Enum):
    PROCESSOS_VIEW = "processos:view"
    PROCESSOS_CREATE = "processos:create"
    PROCESSOS_EDIT = "processos:edit"
    PROCESSOS_DELETE = "processos:delete"
    SEARCH_SEMANTIC = "search:semantic"
    USERS_MANAGE = "users:manage"
    USERS_ROLES = "users:roles"
    TENANT_SETTINGS = "tenant:settings"
    AUDIT_VIEW = "audit:view"
    DATA_EXPORT = "data:export"


ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    "owner": set(Permission),  # Tudo
    "admin": {
        Permission.PROCESSOS_VIEW,
        Permission.PROCESSOS_CREATE,
        Permission.PROCESSOS_EDIT,
        Permission.PROCESSOS_DELETE,
        Permission.SEARCH_SEMANTIC,
        Permission.USERS_MANAGE,
        Permission.USERS_ROLES,
        Permission.AUDIT_VIEW,
        Permission.DATA_EXPORT,
    },
    "advogado": {
        Permission.PROCESSOS_VIEW,
        Permission.PROCESSOS_CREATE,
        Permission.PROCESSOS_EDIT,
        Permission.SEARCH_SEMANTIC,
        Permission.DATA_EXPORT,
    },
    "estagiario": {
        Permission.PROCESSOS_VIEW,
        Permission.PROCESSOS_CREATE,
        Permission.SEARCH_SEMANTIC,
    },
    "leitura": {
        Permission.PROCESSOS_VIEW,
        Permission.SEARCH_SEMANTIC,
    },
}


def has_permission(role: str, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
```

### Critérios de Aceite — Fase 1

- [ ] Tabelas `users`, `refresh_tokens`, `auth_audit_log` criadas
- [ ] RLS em `users` funciona corretamente
- [ ] Constraint de email único por tenant validado
- [ ] Enum `user_role` com os 5 roles
- [ ] `ROLE_PERMISSIONS` cobre todas as combinações da matriz

---

## Fase 2 — Serviço de Autenticação (3-4 dias)

### Objetivo
Implementar login, JWT, refresh token rotation e proteção contra ataques.

### 2.1 — Configuração

```python
# app/core/security_config.py

from pydantic_settings import BaseSettings


class AuthSettings(BaseSettings):
    # JWT
    JWT_SECRET_KEY: str                        # Gerar com: openssl rand -hex 64
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30      # Curta duração
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30        # Longa duração

    # Bcrypt
    BCRYPT_ROUNDS: int = 12                    # ~250ms por hash (bom tradeoff)

    # Rate limiting
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_MINUTES: int = 15

    # Segurança
    PASSWORD_MIN_LENGTH: int = 8

    class Config:
        env_prefix = "AUTH_"
```

### 2.2 — Password Hashing

```python
# app/auth/password.py

import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=12)
    ).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8")
    )
```

### 2.3 — JWT Token Service

```python
# app/auth/token_service.py

import uuid
from datetime import datetime, timedelta, timezone
from hashlib import sha256

import jwt
from app.core.security_config import AuthSettings


class TokenService:
    def __init__(self, settings: AuthSettings):
        self.settings = settings

    def create_access_token(self, user_id: str, tenant_id: str, role: str) -> str:
        payload = {
            "sub": user_id,
            "tid": tenant_id,           # tenant_id no token
            "role": role,
            "type": "access",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(
                minutes=self.settings.ACCESS_TOKEN_EXPIRE_MINUTES
            ),
            "jti": str(uuid.uuid4()),   # ID único do token
        }
        return jwt.encode(payload, self.settings.JWT_SECRET_KEY, algorithm=self.settings.JWT_ALGORITHM)

    def create_refresh_token(self, user_id: str, family_id: str | None = None) -> tuple[str, str]:
        """Retorna (token_plain, token_hash) — só armazenar o hash."""
        token_id = str(uuid.uuid4())
        fid = family_id or str(uuid.uuid4())

        payload = {
            "sub": user_id,
            "fid": fid,
            "type": "refresh",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(
                days=self.settings.REFRESH_TOKEN_EXPIRE_DAYS
            ),
            "jti": token_id,
        }
        token_plain = jwt.encode(payload, self.settings.JWT_SECRET_KEY, algorithm=self.settings.JWT_ALGORITHM)
        token_hash = sha256(token_plain.encode()).hexdigest()

        return token_plain, token_hash, fid

    def decode_token(self, token: str) -> dict:
        """Decodifica e valida o token. Levanta exceção se inválido/expirado."""
        return jwt.decode(
            token,
            self.settings.JWT_SECRET_KEY,
            algorithms=[self.settings.JWT_ALGORITHM],
        )
```

### 2.4 — Auth Service (orquestra login/refresh/logout)

```python
# app/auth/auth_service.py

from app.auth.password import verify_password, hash_password
from app.auth.token_service import TokenService


class AuthService:
    def __init__(self, db, token_service: TokenService, audit_logger):
        self.db = db
        self.tokens = token_service
        self.audit = audit_logger

    async def login(self, email: str, password: str, ip: str, user_agent: str) -> dict:
        # 1. Buscar usuário pelo email (sem RLS — precisa achar em qualquer tenant)
        user = await self._get_user_by_email(email)

        if not user:
            # Timing attack: hash dummy para manter tempo constante
            verify_password("dummy", hash_password("dummy"))
            raise AuthenticationError("Credenciais inválidas")

        # 2. Verificar lockout
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            await self.audit.log(user.tenant_id, user.id, "login_blocked", ip, user_agent)
            remaining = (user.locked_until - datetime.now(timezone.utc)).seconds // 60
            raise AccountLockedError(f"Conta bloqueada. Tente novamente em {remaining} minutos.")

        # 3. Verificar senha
        if not verify_password(password, user.password_hash):
            await self._handle_failed_login(user, ip, user_agent)
            raise AuthenticationError("Credenciais inválidas")

        # 4. Verificar se tenant está ativo
        if not user.tenant.is_active:
            raise AuthenticationError("Escritório desativado. Contate o suporte.")

        # 5. Verificar se usuário está ativo
        if not user.is_active:
            raise AuthenticationError("Conta desativada. Contate o administrador.")

        # 6. Gerar tokens
        access_token = self.tokens.create_access_token(
            str(user.id), str(user.tenant_id), user.role
        )
        refresh_plain, refresh_hash, family_id = self.tokens.create_refresh_token(str(user.id))

        # 7. Salvar refresh token no banco
        await self._save_refresh_token(user.id, refresh_hash, family_id)

        # 8. Reset failed attempts + registrar login
        await self._handle_successful_login(user, ip, user_agent)

        return {
            "access_token": access_token,
            "refresh_token": refresh_plain,
            "token_type": "bearer",
            "expires_in": self.tokens.settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "tenant_name": user.tenant.name,
            },
        }

    async def refresh(self, refresh_token: str) -> dict:
        """
        Refresh Token Rotation:
        - Cada refresh token só pode ser usado UMA vez
        - Ao usar, gera um NOVO refresh token (mesma family)
        - Se um token já usado for apresentado novamente → revogar toda a family
          (indica que o token foi roubado)
        """
        # 1. Decodificar
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

        # 2. Buscar token no banco
        stored = await self._get_refresh_token(token_hash)

        if not stored:
            # Token não encontrado — pode ser reuso de token antigo (ataque)
            # Revogar toda a família como precaução
            await self._revoke_token_family(family_id)
            raise AuthenticationError("Token inválido. Todos os tokens foram revogados por segurança.")

        if stored.is_revoked:
            # Token reusado! Revogar toda a família
            await self._revoke_token_family(family_id)
            raise AuthenticationError("Reuso de token detectado. Faça login novamente.")

        # 3. Revogar o token atual
        await self._revoke_token(stored.id)

        # 4. Buscar usuário
        user = await self._get_user_by_id(user_id)
        if not user or not user.is_active:
            raise AuthenticationError("Conta não encontrada ou desativada.")

        # 5. Gerar novos tokens (mesma family)
        access_token = self.tokens.create_access_token(
            str(user.id), str(user.tenant_id), user.role
        )
        new_refresh_plain, new_refresh_hash, _ = self.tokens.create_refresh_token(
            str(user.id), family_id=family_id
        )

        # 6. Salvar novo refresh token
        await self._save_refresh_token(user.id, new_refresh_hash, family_id, replaced=stored.id)

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_plain,
            "token_type": "bearer",
            "expires_in": self.tokens.settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    async def logout(self, refresh_token: str):
        """Revoga a family inteira do refresh token."""
        try:
            payload = self.tokens.decode_token(refresh_token)
            await self._revoke_token_family(payload["fid"])
        except jwt.InvalidTokenError:
            pass  # Token inválido, nada a revogar

    async def _handle_failed_login(self, user, ip, user_agent):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= self.tokens.settings.MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=self.tokens.settings.LOCKOUT_MINUTES
            )
        await self.db.commit()
        await self.audit.log(user.tenant_id, user.id, "login_failed", ip, user_agent)

    async def _handle_successful_login(self, user, ip, user_agent):
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.audit.log(user.tenant_id, user.id, "login", ip, user_agent)
```

### Critérios de Aceite — Fase 2

- [ ] Login com email/senha funciona e retorna access + refresh token
- [ ] Access token contém `sub`, `tid` (tenant_id), `role`
- [ ] Refresh token rotation funciona (novo token a cada refresh)
- [ ] Reuso de refresh token revoga toda a family
- [ ] Conta bloqueia após 5 tentativas falhas
- [ ] Conta desbloqueada após 15 minutos
- [ ] Proteção contra timing attack no login
- [ ] Logout revoga todos os refresh tokens da sessão

---

## Fase 3 — Middleware de Auth + Integração com Tenant (2 dias)

### Objetivo
Unificar autenticação e tenant resolution num único fluxo. O JWT substitui o header `X-Tenant-ID`.

### 3.1 — Dependency de Auth no FastAPI

```python
# app/auth/dependencies.py

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.permissions import Permission, has_permission
from app.auth.token_service import TokenService
from app.db.tenant import set_current_tenant

security = HTTPBearer()


class CurrentUser:
    """Dados do usuário extraídos do JWT."""
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
                detail=f"Permissão negada: {permission.value}"
            )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_service: TokenService = Depends(get_token_service),
) -> CurrentUser:
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

    # Setar tenant automaticamente a partir do JWT
    set_current_tenant(user.tenant_id)

    return user


def require_permission(permission: Permission):
    """Dependency factory para proteger endpoints."""
    async def _check(user: CurrentUser = Depends(get_current_user)):
        user.require(permission)
        return user
    return _check


# Shortcuts
RequireAdmin = Depends(require_permission(Permission.USERS_MANAGE))
RequireAdvogado = Depends(require_permission(Permission.PROCESSOS_EDIT))
```

### 3.2 — Atualizar o Middleware de Tenant

```python
# app/middleware/tenant.py (atualizado)

class TenantMiddleware(BaseHTTPMiddleware):
    """
    Agora o tenant vem do JWT, não mais do header X-Tenant-ID.
    O middleware só precisa garantir que rotas públicas passem
    e que o DB session tenha o tenant setado.
    """
    PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/auth/login", "/auth/refresh"}

    async def dispatch(self, request: Request, call_next):
        # Rotas públicas — sem auth necessário
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)

        # Para rotas autenticadas, o get_current_user dependency
        # já seta o tenant via set_current_tenant()
        # O middleware garante que o DB session respeita isso

        response = await call_next(request)
        return response
```

### 3.3 — Uso nos Endpoints (antes vs depois)

```python
# ANTES (sem auth):
@router.get("/processos")
async def list_processos(db=Depends(get_db_session)):
    ...

# DEPOIS (com auth + permissions):
@router.get("/processos")
async def list_processos(
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db_session),
):
    # user.tenant_id já setou o RLS
    # Qualquer role pode visualizar processos
    ...

@router.delete("/processos/{processo_id}")
async def delete_processo(
    processo_id: str,
    user: CurrentUser = Depends(require_permission(Permission.PROCESSOS_DELETE)),
    db=Depends(get_db_session),
):
    # Só owner e admin chegam aqui
    ...

@router.get("/admin/audit-log")
async def get_audit_log(
    user: CurrentUser = Depends(require_permission(Permission.AUDIT_VIEW)),
    db=Depends(get_db_session),
):
    ...
```

### 3.4 — DB Session com Tenant do JWT

```python
# app/deps.py (atualizado)

async def get_db_session(request: Request):
    """Agora pega o tenant do contexto (setado pelo get_current_user)."""
    async with async_session_maker() as session:
        tenant_id = get_current_tenant()  # do ContextVar, setado pelo auth dependency
        await set_tenant_on_session(session, tenant_id)
        yield session
```

### Critérios de Aceite — Fase 3

- [ ] Endpoints protegidos retornam 401 sem token
- [ ] Endpoints protegidos retornam 403 sem permissão adequada
- [ ] `tenant_id` extraído do JWT, não mais do header
- [ ] RLS funciona corretamente com tenant do JWT
- [ ] Rotas públicas (/health, /auth/login, /auth/refresh) acessíveis sem token
- [ ] `CurrentUser.can()` e `CurrentUser.require()` funcionam

---

## Fase 4 — Endpoints de Auth (1-2 dias)

### Objetivo
Endpoints de login, refresh, logout e perfil.

### 4.1 — Auth Router

```python
# app/routers/auth.py

from fastapi import APIRouter, Depends, Request

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(data: LoginRequest, request: Request, auth: AuthService = Depends()):
    """Login com email e senha. Retorna access + refresh tokens."""
    result = await auth.login(
        email=data.email,
        password=data.password,
        ip=request.client.host,
        user_agent=request.headers.get("user-agent", ""),
    )
    return result


@router.post("/refresh")
async def refresh_token(data: RefreshRequest, auth: AuthService = Depends()):
    """Troca refresh token por novos access + refresh tokens."""
    return await auth.refresh(data.refresh_token)


@router.post("/logout")
async def logout(data: RefreshRequest, auth: AuthService = Depends()):
    """Revoga a sessão (refresh token family)."""
    await auth.logout(data.refresh_token)
    return {"message": "Logout realizado"}


@router.get("/me")
async def get_profile(user: CurrentUser = Depends(get_current_user), db=Depends(get_db_session)):
    """Retorna dados do usuário logado."""
    db_user = await db.get(User, user.user_id)
    return UserProfile.from_orm(db_user)


@router.patch("/me/password")
async def change_password(
    data: ChangePasswordRequest,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db_session),
    auth: AuthService = Depends(),
):
    """Troca a própria senha. Requer senha atual."""
    await auth.change_password(user.user_id, data.current_password, data.new_password)
    return {"message": "Senha alterada"}
```

### 4.2 — Schemas

```python
# app/schemas/auth.py

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class UserProfile(BaseModel):
    id: str
    name: str
    email: str
    role: str
    tenant_name: str
    last_login_at: str | None

    class Config:
        from_attributes = True
```

### Critérios de Aceite — Fase 4

- [ ] POST /auth/login retorna tokens com credenciais corretas
- [ ] POST /auth/login retorna 401 com credenciais erradas
- [ ] POST /auth/refresh rotaciona tokens corretamente
- [ ] POST /auth/logout invalida a sessão
- [ ] GET /auth/me retorna perfil do usuário logado
- [ ] PATCH /auth/me/password exige senha atual e valida nova senha

---

## Fase 5 — Gestão de Usuários pelo Admin (2 dias)

### Objetivo
Admin do tenant pode criar, editar, desativar e alterar roles de usuários.

### 5.1 — User Management Router

```python
# app/routers/users.py

from fastapi import APIRouter, Depends
from app.auth.dependencies import require_permission
from app.auth.permissions import Permission

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/")
async def list_users(
    user: CurrentUser = Depends(require_permission(Permission.USERS_MANAGE)),
    db=Depends(get_db_session),
):
    """Lista usuários do tenant. Só admin/owner."""
    return await user_service.list_by_tenant(user.tenant_id, db)


@router.post("/", status_code=201)
async def create_user(
    data: CreateUserRequest,
    user: CurrentUser = Depends(require_permission(Permission.USERS_MANAGE)),
    db=Depends(get_db_session),
):
    """
    Admin cria conta para membro da equipe.
    Gera senha temporária que o usuário deve trocar no primeiro login.
    """
    # Admin não pode criar owner; admin só pode criar roles "abaixo" dele
    validate_role_hierarchy(user.role, data.role)

    new_user = await user_service.create(
        tenant_id=user.tenant_id,
        email=data.email,
        name=data.name,
        role=data.role,
        created_by=user.user_id,
        db=db,
    )
    return CreateUserResponse(
        user=UserProfile.from_orm(new_user),
        temporary_password=new_user._temp_password,  # Mostrar apenas uma vez
    )


@router.patch("/{user_id}/role")
async def change_role(
    user_id: str,
    data: ChangeRoleRequest,
    user: CurrentUser = Depends(require_permission(Permission.USERS_ROLES)),
    db=Depends(get_db_session),
):
    """Altera role de um usuário. Respeita hierarquia."""
    validate_role_hierarchy(user.role, data.new_role)
    await user_service.change_role(user_id, data.new_role, changed_by=user.user_id, db=db)
    return {"message": f"Role alterado para {data.new_role}"}


@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    user: CurrentUser = Depends(require_permission(Permission.USERS_MANAGE)),
    db=Depends(get_db_session),
):
    """Desativa usuário (soft delete). Revoga todos os tokens."""
    if user_id == user.user_id:
        raise HTTPException(400, "Não pode desativar a si mesmo")
    await user_service.deactivate(user_id, db)
    return {"message": "Usuário desativado"}


@router.post("/{user_id}/reset-password")
async def admin_reset_password(
    user_id: str,
    user: CurrentUser = Depends(require_permission(Permission.USERS_MANAGE)),
    db=Depends(get_db_session),
):
    """Admin reseta a senha de um usuário. Gera nova senha temporária."""
    temp_password = await user_service.reset_password(user_id, db)
    return {"temporary_password": temp_password}
```

### 5.2 — Hierarquia de Roles

```python
# app/auth/role_hierarchy.py

ROLE_LEVEL = {
    "owner": 100,
    "admin": 80,
    "advogado": 50,
    "estagiario": 30,
    "leitura": 10,
}


def validate_role_hierarchy(actor_role: str, target_role: str):
    """
    Um usuário só pode gerenciar roles de nível inferior ao seu.
    Owner pode tudo. Admin não pode criar/alterar outros admins ou owners.
    """
    actor_level = ROLE_LEVEL.get(actor_role, 0)
    target_level = ROLE_LEVEL.get(target_role, 0)

    if target_level >= actor_level:
        raise HTTPException(
            status_code=403,
            detail=f"Você ({actor_role}) não pode atribuir o role {target_role}"
        )
```

### 5.3 — Seed do Primeiro Usuário (Owner)

```python
# scripts/create_owner.py

"""
Roda via CLI ao criar um novo tenant.
Cria o owner que depois cria os demais pelo painel.

Uso: python scripts/create_owner.py --tenant-slug silva-associados \
     --email admin@silva.adv.br --name "Dr. Silva" --password "SenhaSegura123"
"""

import asyncio
import argparse
from app.auth.password import hash_password


async def create_owner(slug: str, email: str, name: str, password: str):
    async with get_admin_session() as db:  # Sem RLS
        tenant = await get_tenant_by_slug(db, slug)
        if not tenant:
            print(f"Tenant '{slug}' não encontrado")
            return

        user = User(
            tenant_id=tenant.id,
            email=email,
            name=name,
            password_hash=hash_password(password),
            role="owner",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        print(f"Owner criado: {email} ({name}) no tenant {tenant.name}")
```

### Critérios de Aceite — Fase 5

- [ ] Admin pode criar usuários com role inferior ao seu
- [ ] Admin não pode criar outro admin (só owner pode)
- [ ] Admin não pode desativar a si mesmo
- [ ] Senha temporária gerada no create é exibida apenas uma vez
- [ ] Reset de senha revoga todos os refresh tokens do usuário
- [ ] Audit log registra criação, desativação e mudança de role
- [ ] Script `create_owner.py` funciona para bootstrap

---

## Fase 6 — Frontend Auth (2-3 dias)

### Objetivo
Tela de login, gerenciamento de tokens no React, e proteção de rotas.

### 6.1 — Auth Store

```tsx
// src/stores/authStore.ts

import { create } from 'zustand';

interface AuthState {
  accessToken: string | null;
  user: UserProfile | null;
  isAuthenticated: boolean;

  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshTokens: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  accessToken: null,
  user: null,
  isAuthenticated: false,

  login: async (email, password) => {
    const response = await api.post('/auth/login', { email, password });
    const { access_token, refresh_token, user } = response.data;

    // Refresh token no httpOnly cookie (ideal) ou memory
    // NUNCA em localStorage
    setRefreshToken(refresh_token);

    set({ accessToken: access_token, user, isAuthenticated: true });
  },

  logout: async () => {
    try {
      await api.post('/auth/logout', { refresh_token: getRefreshToken() });
    } finally {
      clearRefreshToken();
      set({ accessToken: null, user: null, isAuthenticated: false });
    }
  },

  refreshTokens: async () => {
    const refresh = getRefreshToken();
    if (!refresh) throw new Error('No refresh token');

    const response = await api.post('/auth/refresh', { refresh_token: refresh });
    const { access_token, refresh_token: new_refresh } = response.data;

    setRefreshToken(new_refresh);
    set({ accessToken: access_token });
  },
}));
```

### 6.2 — Axios Interceptor com Auto-Refresh

```tsx
// src/lib/api.ts

import axios from 'axios';
import { useAuthStore } from '../stores/authStore';

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL });

// Request: injeta access token
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response: auto-refresh em 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;

    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;

      try {
        await useAuthStore.getState().refreshTokens();
        // Retry com novo token
        const newToken = useAuthStore.getState().accessToken;
        original.headers.Authorization = `Bearer ${newToken}`;
        return api(original);
      } catch {
        // Refresh falhou — forçar logout
        useAuthStore.getState().logout();
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

export default api;
```

### 6.3 — Proteção de Rotas

```tsx
// src/components/ProtectedRoute.tsx

import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { Permission, hasPermission } from '../lib/permissions';

interface Props {
  children: React.ReactNode;
  permission?: Permission;
}

export function ProtectedRoute({ children, permission }: Props) {
  const { isAuthenticated, user } = useAuthStore();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (permission && !hasPermission(user!.role, permission)) {
    return <Navigate to="/403" replace />;
  }

  return <>{children}</>;
}

// Uso no router:
<Route path="/processos" element={
  <ProtectedRoute>
    <ProcessosPage />
  </ProtectedRoute>
} />

<Route path="/admin/users" element={
  <ProtectedRoute permission="users:manage">
    <UsersManagementPage />
  </ProtectedRoute>
} />
```

### Critérios de Aceite — Fase 6

- [ ] Tela de login funcional com feedback de erro
- [ ] Token armazenado em memória (nunca localStorage)
- [ ] Auto-refresh transparente em 401
- [ ] Refresh falho redireciona para login
- [ ] Rotas protegidas por role
- [ ] Menu lateral mostra/esconde itens conforme permissão
- [ ] Logout limpa estado e redireciona

---

## Fase 7 — Segurança e Hardening (1-2 dias)

### Objetivo
Rate limiting, CORS, cleanup de tokens e proteções adicionais.

### 7.1 — Rate Limiting no Login

```python
# app/middleware/rate_limit.py

from fastapi import Request, HTTPException
import redis.asyncio as redis


class LoginRateLimiter:
    """
    Rate limiting por IP no endpoint de login.
    Complementa o lockout por conta (que é por usuário).
    """
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.max_attempts = 20     # Por IP
        self.window_seconds = 900  # 15 minutos

    async def check(self, ip: str):
        key = f"login_rate:{ip}"
        attempts = await self.redis.incr(key)
        if attempts == 1:
            await self.redis.expire(key, self.window_seconds)
        if attempts > self.max_attempts:
            raise HTTPException(429, "Muitas tentativas de login. Tente novamente em 15 minutos.")
```

### 7.2 — CORS

```python
# app/main.py

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://*.monitor.exemplo.com",  # Subdomains dos tenants
        "http://localhost:5173",            # Dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 7.3 — Cleanup de Tokens Expirados

```python
# app/workers/auth_cleanup.py

import dramatiq


@dramatiq.actor(queue_name="maintenance")
def cleanup_expired_tokens():
    """Roda diariamente. Remove refresh tokens expirados."""
    deleted = db.execute(
        text("DELETE FROM refresh_tokens WHERE expires_at < now()")
    )
    logger.info(f"Removidos {deleted.rowcount} refresh tokens expirados")


@dramatiq.actor(queue_name="maintenance")
def cleanup_old_audit_logs():
    """Remove audit logs com mais de 90 dias."""
    deleted = db.execute(
        text("DELETE FROM auth_audit_log WHERE created_at < now() - interval '90 days'")
    )
    logger.info(f"Removidos {deleted.rowcount} registros de audit log")
```

### 7.4 — Headers de Segurança

```python
# app/middleware/security_headers.py

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Cache-Control"] = "no-store"  # Evitar cache de dados sensíveis
        return response
```

### Critérios de Aceite — Fase 7

- [ ] Rate limiting bloqueia IP após 20 tentativas em 15 min
- [ ] CORS configurado para domínios permitidos
- [ ] Cleanup de tokens expirados roda diariamente
- [ ] Headers de segurança presentes em todas as respostas
- [ ] Tokens nunca logados em plaintext nos logs

---

## Cronograma Resumido

| Semana   | Fases     | Entregas                                                     |
|----------|-----------|--------------------------------------------------------------|
| Semana 1 | 1 + 2     | Schema users/roles, auth service, JWT, refresh rotation       |
| Semana 2 | 3 + 4 + 5 | Middleware auth, endpoints de auth e user management           |
| Semana 3 | 6 + 7     | Frontend auth, rate limiting, hardening, cleanup               |

---

## Riscos e Mitigações

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| JWT secret vazado | Acesso total ao sistema | Rotacionar secret; invalidar todos os tokens |
| Refresh token roubado | Sessão hijacked | Token rotation detecta reuso e revoga family |
| Brute force no login | Account takeover | Lockout por conta (5 tentativas) + rate limit por IP |
| RLS bypassado em nova query | Data leak | Testes de isolamento obrigatórios a cada endpoint novo |
| Senha fraca do owner | Comprometimento do tenant | Validação de complexidade mínima |

---

## Decisões Futuras (fora do escopo atual)

- **MFA (TOTP)**: adicionar como segunda fase de segurança quando clientes exigirem
- **Password reset por email**: quando tiver SMTP configurado (por enquanto admin reseta)
- **SSO / OAuth2**: se precisar integrar com sistemas do escritório (AD, Google Workspace)
- **API Keys**: para integrações programáticas (webhooks, automações)
- **Session management UI**: tela pra usuário ver/revogar sessões ativas