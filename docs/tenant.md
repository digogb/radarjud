# Plano de Implementação — Multi-Tenancy no DJE Monitor

## Visão Geral

Transformar o DJE Monitor de single-tenant para multi-tenant, permitindo que múltiplos escritórios de advocacia operem na mesma instância com isolamento total de dados.

### Stack Atual (referência)

| Componente       | Tecnologia                     |
|------------------|--------------------------------|
| API              | FastAPI                        |
| Task Queue       | Dramatiq + Redis               |
| Banco            | PostgreSQL                     |
| Vector Store     | Qdrant                         |
| Embeddings       | Nomic AI (nomic-embed-text-v1.5) |
| Cache/Broker     | Redis                          |
| Deploy           | Docker Compose                 |
| Frontend         | React + Vite                   |

### Princípio de Isolamento

Tenant = Escritório de advocacia. Cada tenant tem seus dados completamente isolados: processos, publicações, embeddings, filas de processamento e cache. Um tenant nunca vê dados de outro.

---

## Fase 1 — Modelo de Tenant e Banco de Dados (3-4 dias)

### Objetivo
Criar a estrutura de tenants no PostgreSQL com isolamento via `tenant_id` e Row-Level Security (RLS).

### 1.1 — Tabela de Tenants

```sql
-- migrations/001_create_tenants.sql

CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,              -- "Escritório Silva & Associados"
    slug VARCHAR(100) UNIQUE NOT NULL,       -- "silva-associados" (usado em URLs/subdomains)
    is_active BOOLEAN DEFAULT true,
    settings JSONB DEFAULT '{}',             -- configurações específicas (tribunais, limites, etc)
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_tenants_slug ON tenants(slug);
CREATE INDEX idx_tenants_active ON tenants(is_active) WHERE is_active = true;
```

### 1.2 — Adicionar `tenant_id` em todas as tabelas existentes

```sql
-- migrations/002_add_tenant_id.sql

-- Para cada tabela existente (processos, publicacoes, pessoas, movimentacoes, etc):
ALTER TABLE processos ADD COLUMN tenant_id UUID NOT NULL REFERENCES tenants(id);
ALTER TABLE publicacoes ADD COLUMN tenant_id UUID NOT NULL REFERENCES tenants(id);
ALTER TABLE pessoas ADD COLUMN tenant_id UUID NOT NULL REFERENCES tenants(id);
ALTER TABLE movimentacoes ADD COLUMN tenant_id UUID NOT NULL REFERENCES tenants(id);
ALTER TABLE documentos ADD COLUMN tenant_id UUID NOT NULL REFERENCES tenants(id);

-- Índices compostos (tenant_id sempre primeiro para query performance)
CREATE INDEX idx_processos_tenant ON processos(tenant_id);
CREATE INDEX idx_processos_tenant_numero ON processos(tenant_id, numero_processo);
CREATE INDEX idx_publicacoes_tenant ON publicacoes(tenant_id);
CREATE INDEX idx_publicacoes_tenant_data ON publicacoes(tenant_id, data_publicacao DESC);
CREATE INDEX idx_pessoas_tenant ON pessoas(tenant_id);
CREATE INDEX idx_pessoas_tenant_cpf ON pessoas(tenant_id, cpf);
```

### 1.3 — Row-Level Security (RLS)

```sql
-- migrations/003_rls_policies.sql

-- Habilitar RLS em todas as tabelas com tenant_id
ALTER TABLE processos ENABLE ROW LEVEL SECURITY;
ALTER TABLE publicacoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE pessoas ENABLE ROW LEVEL SECURITY;
ALTER TABLE movimentacoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE documentos ENABLE ROW LEVEL SECURITY;

-- Política: só acessa rows do tenant setado na sessão
CREATE POLICY tenant_isolation_processos ON processos
    USING (tenant_id = current_setting('app.current_tenant')::UUID);

CREATE POLICY tenant_isolation_publicacoes ON publicacoes
    USING (tenant_id = current_setting('app.current_tenant')::UUID);

CREATE POLICY tenant_isolation_pessoas ON pessoas
    USING (tenant_id = current_setting('app.current_tenant')::UUID);

CREATE POLICY tenant_isolation_movimentacoes ON movimentacoes
    USING (tenant_id = current_setting('app.current_tenant')::UUID);

CREATE POLICY tenant_isolation_documentos ON documentos
    USING (tenant_id = current_setting('app.current_tenant')::UUID);

-- IMPORTANTE: criar um role separado para a aplicação
-- O superuser bypassa RLS por padrão
CREATE ROLE app_user WITH LOGIN PASSWORD 'senha_segura';
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;

-- Role admin (para migrations, backfill, etc) — bypassa RLS
CREATE ROLE app_admin WITH LOGIN PASSWORD 'senha_admin' SUPERUSER;
```

### 1.4 — Tenant Context no SQLAlchemy/DB Session

```python
# app/db/tenant.py

from contextvars import ContextVar
from sqlalchemy.ext.asyncio import AsyncSession

_current_tenant: ContextVar[str | None] = ContextVar("current_tenant", default=None)


def get_current_tenant() -> str:
    tenant = _current_tenant.get()
    if not tenant:
        raise RuntimeError("Tenant não definido no contexto atual")
    return tenant


def set_current_tenant(tenant_id: str):
    _current_tenant.set(tenant_id)


async def set_tenant_on_session(session: AsyncSession, tenant_id: str):
    """Seta o tenant na sessão do PostgreSQL para RLS funcionar."""
    await session.execute(
        text("SET app.current_tenant = :tenant_id"),
        {"tenant_id": tenant_id}
    )
```

### Critérios de Aceite — Fase 1

- [ ] Tabela `tenants` criada com pelo menos 2 tenants de teste
- [ ] Todas as tabelas existentes têm `tenant_id` NOT NULL
- [ ] RLS habilitado e testado: query como `app_user` sem tenant setado retorna 0 rows
- [ ] Query com tenant setado retorna apenas dados daquele tenant
- [ ] Índices compostos criados e validados com `EXPLAIN ANALYZE`

---

## Fase 2 — Middleware de Tenant na API (2-3 dias)

### Objetivo
Identificar o tenant em cada request e propagar o contexto para toda a stack.

### 2.1 — Estratégia de Identificação

Suporte a 3 modos (em ordem de prioridade):

1. **Header `X-Tenant-ID`** — para chamadas internas/API
2. **Subdomain** — `silva-associados.monitor.exemplo.com` (futuro)
3. **Query param `?tenant=`** — para debug/desenvolvimento

### 2.2 — Middleware FastAPI

```python
# app/middleware/tenant.py

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.db.tenant import set_current_tenant
from app.services.tenant_service import TenantService


class TenantMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, tenant_service: TenantService):
        super().__init__(app)
        self.tenant_service = tenant_service

    async def dispatch(self, request: Request, call_next):
        # Rotas públicas (health, docs, etc)
        if request.url.path in ("/health", "/docs", "/openapi.json"):
            return await call_next(request)

        # Admin routes (gerenciamento de tenants)
        if request.url.path.startswith("/admin/"):
            return await call_next(request)

        tenant_id = await self._resolve_tenant(request)
        if not tenant_id:
            raise HTTPException(
                status_code=400,
                detail="Tenant não identificado. Envie header X-Tenant-ID."
            )

        # Validar que o tenant existe e está ativo
        tenant = await self.tenant_service.get_active_tenant(tenant_id)
        if not tenant:
            raise HTTPException(status_code=403, detail="Tenant inativo ou inexistente.")

        # Setar no contexto
        set_current_tenant(str(tenant.id))
        request.state.tenant = tenant
        request.state.tenant_id = str(tenant.id)

        return await call_next(request)

    async def _resolve_tenant(self, request: Request) -> str | None:
        # 1. Header explícito
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return tenant_id

        # 2. Subdomain
        host = request.headers.get("host", "")
        parts = host.split(".")
        if len(parts) >= 3:
            slug = parts[0]
            tenant = await self.tenant_service.get_by_slug(slug)
            if tenant:
                return str(tenant.id)

        # 3. Query param (apenas em dev)
        if settings.ENVIRONMENT == "development":
            return request.query_params.get("tenant")

        return None
```

### 2.3 — Dependency Injection para DB Session com Tenant

```python
# app/deps.py

from fastapi import Depends, Request
from app.db.session import async_session_maker
from app.db.tenant import set_tenant_on_session


async def get_db_session(request: Request):
    """Session já configurada com o tenant do request."""
    async with async_session_maker() as session:
        tenant_id = request.state.tenant_id
        await set_tenant_on_session(session, tenant_id)
        yield session
```

### 2.4 — Tenant Service

```python
# app/services/tenant_service.py

from functools import lru_cache
from app.models import Tenant


class TenantService:
    def __init__(self, db):
        self.db = db
        self._cache: dict[str, Tenant] = {}  # cache em memória, TTL via Redis

    async def get_active_tenant(self, tenant_id: str) -> Tenant | None:
        # Cache local (evita hit no banco a cada request)
        if tenant_id in self._cache:
            tenant = self._cache[tenant_id]
            return tenant if tenant.is_active else None

        tenant = await self.db.get(Tenant, tenant_id)
        if tenant:
            self._cache[tenant_id] = tenant
        return tenant if tenant and tenant.is_active else None

    async def get_by_slug(self, slug: str) -> Tenant | None:
        result = await self.db.execute(
            select(Tenant).where(Tenant.slug == slug, Tenant.is_active == True)
        )
        return result.scalar_one_or_none()

    async def create_tenant(self, name: str, slug: str, settings: dict = None) -> Tenant:
        tenant = Tenant(name=name, slug=slug, settings=settings or {})
        self.db.add(tenant)
        await self.db.commit()
        return tenant
```

### Critérios de Aceite — Fase 2

- [ ] Request sem `X-Tenant-ID` retorna 400
- [ ] Request com tenant inválido retorna 403
- [ ] Request com tenant válido: `request.state.tenant_id` disponível em todos os endpoints
- [ ] DB session já tem RLS ativo para o tenant correto
- [ ] Rotas `/health` e `/docs` funcionam sem tenant
- [ ] Cache de tenants funciona (2º request não bate no banco)

---

## Fase 3 — Isolamento no Qdrant (2 dias)

### Objetivo
Garantir que embeddings/vetores de cada tenant fiquem isolados no Qdrant.

### 3.1 — Estratégia: Collection por Tenant

```python
# app/services/qdrant_tenant.py

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams


class QdrantTenantManager:
    VECTOR_SIZE = 256  # Matryoshka truncado
    COLLECTION_PREFIX = "dje_"

    def __init__(self, client: QdrantClient):
        self.client = client

    def collection_name(self, tenant_id: str) -> str:
        """Cada tenant tem sua própria collection."""
        return f"{self.COLLECTION_PREFIX}{tenant_id.replace('-', '_')}"

    async def ensure_collection(self, tenant_id: str):
        """Cria collection do tenant se não existir."""
        name = self.collection_name(tenant_id)
        collections = await self.client.get_collections()
        existing = [c.name for c in collections.collections]

        if name not in existing:
            await self.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=self.VECTOR_SIZE,
                    distance=Distance.COSINE,
                ),
            )
            # Criar índices de payload para filtros híbridos
            await self.client.create_payload_index(
                collection_name=name,
                field_name="tribunal",
                field_schema="keyword",
            )
            await self.client.create_payload_index(
                collection_name=name,
                field_name="tipo",  # publicacao, movimentacao, etc
                field_schema="keyword",
            )

    async def delete_collection(self, tenant_id: str):
        """Remove todos os dados de um tenant do Qdrant."""
        name = self.collection_name(tenant_id)
        await self.client.delete_collection(name)
```

### 3.2 — Atualizar Embedding Service

```python
# app/services/embedding_service.py (modificações)

class EmbeddingService:
    def __init__(self, qdrant_manager: QdrantTenantManager, model):
        self.qdrant = qdrant_manager
        self.model = model

    async def index_document(self, tenant_id: str, doc_id: str, text: str, metadata: dict):
        collection = self.qdrant.collection_name(tenant_id)
        vector = self.model.encode(f"search_document: {text}")
        vector_truncated = vector[:256]

        await self.qdrant.client.upsert(
            collection_name=collection,
            points=[{
                "id": doc_id,
                "vector": vector_truncated.tolist(),
                "payload": {**metadata, "text_preview": text[:500]},
            }],
        )

    async def search(self, tenant_id: str, query: str, filters: dict = None, top_k: int = 20):
        collection = self.qdrant.collection_name(tenant_id)
        query_vector = self.model.encode(f"search_query: {query}")
        query_vector_truncated = query_vector[:256]

        qdrant_filter = self._build_filter(filters) if filters else None

        return await self.qdrant.client.search(
            collection_name=collection,
            query_vector=query_vector_truncated.tolist(),
            query_filter=qdrant_filter,
            limit=top_k,
        )
```

### Critérios de Aceite — Fase 3

- [ ] Ao criar um tenant, collection é criada automaticamente no Qdrant
- [ ] Busca semântica do tenant A não retorna resultados do tenant B
- [ ] Índices de payload criados para filtros híbridos
- [ ] Ao desativar/deletar tenant, collection é removida do Qdrant

---

## Fase 4 — Isolamento no Dramatiq e Redis (2-3 dias)

### Objetivo
Garantir que tasks e cache de cada tenant fiquem isolados e que um tenant com muitos processos não bloqueie a fila dos outros.

### 4.1 — Queue Routing por Tenant

```python
# app/workers/tenant_tasks.py

import dramatiq
from app.db.tenant import set_current_tenant


def tenant_task(fn):
    """Decorator que injeta o tenant_id no contexto do worker."""
    @dramatiq.actor
    def wrapper(tenant_id: str, *args, **kwargs):
        set_current_tenant(tenant_id)
        return fn(tenant_id, *args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper


# Uso:
@tenant_task
def sync_processo(tenant_id: str, processo_id: str):
    """O tenant_id já está no contexto."""
    # ... lógica de sync ...


@tenant_task
def indexar_publicacao(tenant_id: str, publicacao_id: str):
    """Indexa no Qdrant da collection correta."""
    # ... lógica de indexação ...
```

### 4.2 — Prioridade por Tenant (evitar noisy neighbor)

```python
# app/workers/scheduler.py

from dramatiq.rate_limits import ConcurrentRateLimiter
from dramatiq.rate_limits.backends import RedisBackend

backend = RedisBackend(url=settings.REDIS_URL)

# Limitar tasks simultâneas por tenant (evita que um monopolize workers)
def get_tenant_limiter(tenant_id: str) -> ConcurrentRateLimiter:
    return ConcurrentRateLimiter(
        backend,
        key=f"tenant_limit:{tenant_id}",
        limit=5,  # máximo 5 tasks simultâneas por tenant
    )


@dramatiq.actor(queue_name="sync")
def sync_processos_tenant(tenant_id: str):
    limiter = get_tenant_limiter(tenant_id)
    with limiter.acquire():
        set_current_tenant(tenant_id)
        processos = get_processos_para_sync(tenant_id)
        for processo in processos:
            sync_processo.send(tenant_id, processo.id)
```

### 4.3 — Redis Key Isolation

```python
# app/cache/tenant_cache.py

import redis.asyncio as redis


class TenantCache:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def _key(self, tenant_id: str, key: str) -> str:
        """Todas as keys no Redis são prefixadas com tenant_id."""
        return f"t:{tenant_id}:{key}"

    async def get(self, tenant_id: str, key: str) -> str | None:
        return await self.redis.get(self._key(tenant_id, key))

    async def set(self, tenant_id: str, key: str, value: str, ttl: int = 3600):
        await self.redis.set(self._key(tenant_id, key), value, ex=ttl)

    async def delete_tenant_data(self, tenant_id: str):
        """Remove todo cache de um tenant."""
        pattern = f"t:{tenant_id}:*"
        async for key in self.redis.scan_iter(match=pattern):
            await self.redis.delete(key)
```

### Critérios de Aceite — Fase 4

- [ ] Tasks sempre recebem `tenant_id` e setam contexto corretamente
- [ ] Rate limiter por tenant funciona: max 5 tasks simultâneas por tenant
- [ ] Cache do tenant A não é acessível pelo tenant B
- [ ] Deletar tenant limpa todas as keys do Redis
- [ ] Sync diária roda para todos os tenants ativos em paralelo

---

## Fase 5 — API Admin de Tenants (1-2 dias)

### Objetivo
Endpoints para gerenciar o ciclo de vida dos tenants.

### 5.1 — Endpoints

```python
# app/routers/admin.py

from fastapi import APIRouter, Depends

router = APIRouter(prefix="/admin/tenants", tags=["admin"])


@router.post("/", status_code=201)
async def create_tenant(data: TenantCreate, db=Depends(get_admin_db)):
    """
    Cria tenant + collection no Qdrant + setup inicial.
    """
    tenant = await tenant_service.create_tenant(data.name, data.slug, data.settings)
    await qdrant_manager.ensure_collection(str(tenant.id))
    return TenantResponse.from_orm(tenant)


@router.get("/")
async def list_tenants(db=Depends(get_admin_db)):
    """Lista todos os tenants com stats básicas."""
    tenants = await tenant_service.list_all()
    return [TenantWithStats.from_tenant(t) for t in tenants]


@router.get("/{tenant_id}/stats")
async def tenant_stats(tenant_id: str, db=Depends(get_admin_db)):
    """
    Stats do tenant: total processos, publicações, uso de storage,
    última sync, tamanho da collection no Qdrant.
    """
    return await tenant_service.get_stats(tenant_id)


@router.patch("/{tenant_id}")
async def update_tenant(tenant_id: str, data: TenantUpdate, db=Depends(get_admin_db)):
    return await tenant_service.update(tenant_id, data)


@router.post("/{tenant_id}/deactivate")
async def deactivate_tenant(tenant_id: str, db=Depends(get_admin_db)):
    """Desativa tenant (soft delete). Dados mantidos."""
    return await tenant_service.deactivate(tenant_id)


@router.delete("/{tenant_id}")
async def delete_tenant(tenant_id: str, db=Depends(get_admin_db)):
    """
    HARD DELETE. Remove:
    - Collection do Qdrant
    - Keys do Redis
    - Dados do PostgreSQL
    Requer confirmação.
    """
    await qdrant_manager.delete_collection(tenant_id)
    await tenant_cache.delete_tenant_data(tenant_id)
    await tenant_service.hard_delete(tenant_id)
    return {"status": "deleted"}
```

### 5.2 — Schemas

```python
# app/schemas/tenant.py

from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    slug: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-z0-9-]+$")
    settings: dict = Field(default_factory=dict)
    # settings pode incluir:
    # - tribunais: ["TJSP", "TJRJ", "TRF3"]
    # - max_processos: 10000
    # - sync_horario: "02:00"


class TenantUpdate(BaseModel):
    name: str | None = None
    settings: dict | None = None
    is_active: bool | None = None


class TenantResponse(BaseModel):
    id: str
    name: str
    slug: str
    is_active: bool
    settings: dict
    created_at: str


class TenantWithStats(TenantResponse):
    total_processos: int
    total_publicacoes: int
    total_vetores: int
    ultima_sync: str | None
```

### Critérios de Aceite — Fase 5

- [ ] CRUD completo de tenants via API
- [ ] Criar tenant também cria collection no Qdrant
- [ ] Deletar tenant limpa Qdrant + Redis + Postgres
- [ ] Endpoint de stats retorna métricas reais
- [ ] Validação de slug (único, lowercase, sem espaços)

---

## Fase 6 — Frontend Multi-Tenant (2-3 dias)

### Objetivo
Adaptar o frontend React para operar em contexto de tenant.

### 6.1 — Tenant Context no React

```tsx
// src/contexts/TenantContext.tsx

interface TenantContextType {
  tenantId: string;
  tenantName: string;
  settings: TenantSettings;
}

const TenantContext = createContext<TenantContextType | null>(null);

export function TenantProvider({ children }: { children: React.ReactNode }) {
  const tenantId = resolveTenantFromUrl(); // subdomain ou path
  const { data: tenant } = useQuery(['tenant', tenantId], () => fetchTenant(tenantId));

  if (!tenant) return <TenantLoadingScreen />;

  return (
    <TenantContext.Provider value={tenant}>
      {children}
    </TenantContext.Provider>
  );
}

export const useTenant = () => {
  const ctx = useContext(TenantContext);
  if (!ctx) throw new Error("useTenant deve ser usado dentro de TenantProvider");
  return ctx;
};
```

### 6.2 — API Client com Tenant Header

```tsx
// src/lib/api.ts

import axios from 'axios';
import { getCurrentTenantId } from './tenant';

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL });

// Interceptor: injeta tenant em toda request
api.interceptors.request.use((config) => {
  const tenantId = getCurrentTenantId();
  if (tenantId) {
    config.headers['X-Tenant-ID'] = tenantId;
  }
  return config;
});

export default api;
```

### 6.3 — Seletor de Tenant (para admin/multi-escritório)

```tsx
// src/components/TenantSelector.tsx
// Dropdown no header para alternar entre escritórios (se o usuário tiver acesso a mais de um)

export function TenantSelector() {
  const { tenantId } = useTenant();
  const { data: tenants } = useQuery(['tenants'], fetchUserTenants);

  return (
    <Select value={tenantId} onValueChange={switchTenant}>
      {tenants?.map(t => (
        <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
      ))}
    </Select>
  );
}
```

### Critérios de Aceite — Fase 6

- [ ] Frontend resolve tenant via subdomain ou seletor
- [ ] Todas as chamadas API incluem `X-Tenant-ID`
- [ ] Dashboard mostra apenas dados do tenant ativo
- [ ] Troca de tenant recarrega dados corretamente
- [ ] Admin consegue visualizar stats de todos os tenants

---

## Fase 7 — Sync Diária Multi-Tenant (1-2 dias)

### Objetivo
Adaptar o scheduler de sync diária para rodar para todos os tenants ativos.

### 7.1 — Orchestrator de Sync

```python
# app/workers/sync_orchestrator.py

@dramatiq.actor(queue_name="scheduler")
def sync_diaria_todos_tenants():
    """
    Executado pelo cron diário.
    Dispara sync para cada tenant ativo em paralelo.
    """
    tenants = get_active_tenants()  # query sem RLS (role admin)

    for tenant in tenants:
        # Cada tenant recebe sua própria task com rate limiting
        sync_tenant_processos.send(str(tenant.id))


@dramatiq.actor(queue_name="sync", max_retries=2)
def sync_tenant_processos(tenant_id: str):
    """Sync todos os processos de um tenant."""
    limiter = get_tenant_limiter(tenant_id)
    set_current_tenant(tenant_id)

    processos = get_processos_para_sync(tenant_id)
    tenant_settings = get_tenant_settings(tenant_id)
    tribunais = tenant_settings.get("tribunais", [])

    for processo in processos:
        for tribunal in tribunais:
            with limiter.acquire():
                sync_processo_tribunal.send(tenant_id, processo.id, tribunal)

    # Registrar última sync
    update_tenant_last_sync(tenant_id)
```

### 7.2 — Cron no Docker Compose

```yaml
# docker-compose.yml — adicionar ao worker
services:
  scheduler:
    build: ./apps/api
    command: >
      sh -c "while true; do
        python -c 'from app.workers.sync_orchestrator import sync_diaria_todos_tenants; sync_diaria_todos_tenants.send()'
        sleep 86400
      done"
    depends_on:
      - redis
      - db
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://app_admin:senha@db:5432/processos
```

### Critérios de Aceite — Fase 7

- [ ] Sync diária roda para todos os tenants ativos
- [ ] Tenant inativo é ignorado na sync
- [ ] Rate limiting por tenant funciona sob carga
- [ ] Última sync registrada por tenant
- [ ] Falha em um tenant não afeta os outros

---

## Fase 8 — Testes e Validação (2-3 dias)

### 8.1 — Testes de Isolamento

```python
# tests/test_tenant_isolation.py

import pytest

@pytest.fixture
async def tenant_a():
    return await create_test_tenant("Escritório A", "escritorio-a")

@pytest.fixture
async def tenant_b():
    return await create_test_tenant("Escritório B", "escritorio-b")


async def test_processo_isolation(tenant_a, tenant_b, db):
    """Processo do tenant A não aparece para tenant B."""
    # Criar processo no tenant A
    set_tenant(db, tenant_a.id)
    await create_processo(db, tenant_a.id, "0001234-56.2024.8.26.0100")

    # Buscar no tenant B: deve retornar vazio
    set_tenant(db, tenant_b.id)
    result = await get_processos(db)
    assert len(result) == 0


async def test_qdrant_isolation(tenant_a, tenant_b, qdrant):
    """Busca semântica do tenant A não retorna vetores do tenant B."""
    await index_doc(tenant_a.id, "Execução fiscal IPTU dívida ativa")
    await index_doc(tenant_b.id, "Divórcio consensual partilha bens")

    results = await search(tenant_a.id, "dívida tributária")
    assert all(r.tenant_id == tenant_a.id for r in results)


async def test_cache_isolation(tenant_a, tenant_b, cache):
    """Cache do tenant A não é acessível pelo tenant B."""
    await cache.set(tenant_a.id, "key1", "valor_a")

    result = await cache.get(tenant_b.id, "key1")
    assert result is None


async def test_rls_without_tenant_blocks_access(db):
    """Sem tenant setado, RLS bloqueia tudo."""
    # Não setar tenant
    result = await db.execute(text("SELECT * FROM processos"))
    assert len(result.fetchall()) == 0
```

### 8.2 — Teste de Carga

```bash
# Simular 5 tenants com 1000 processos cada
python scripts/seed_tenants.py --count 5 --processos-per-tenant 1000

# Rodar sync simultâneo e verificar que não há crosstalk
python scripts/stress_test_sync.py --parallel-tenants 5

# Verificar performance de busca semântica por tenant
python scripts/benchmark_search.py --tenant silva-associados --queries 100
```

### Critérios de Aceite — Fase 8

- [ ] Todos os testes de isolamento passam
- [ ] Teste de carga com 5 tenants simultâneos sem erro
- [ ] Nenhum caso de data leak entre tenants
- [ ] Performance de busca semântica < 200ms por query
- [ ] Sync diária completa em < 1h para 5 tenants × 1000 processos

---

## Cronograma Resumido

| Semana   | Fases     | Entregas                                                 |
|----------|-----------|----------------------------------------------------------|
| Semana 1 | 1 + 2     | Schema multi-tenant, RLS, middleware, tenant context      |
| Semana 2 | 3 + 4 + 5 | Qdrant isolado, Dramatiq tenant-aware, API admin          |
| Semana 3 | 6 + 7 + 8 | Frontend adaptado, sync multi-tenant, testes completos    |

---

## Riscos e Mitigações

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| RLS bypassado por role errado | Data leak | Usar `app_user` role na aplicação; `app_admin` só para migrations |
| Noisy neighbor (tenant com 50k processos) | Degradação para outros | Rate limiting por tenant no Dramatiq + connection pool separado |
| Collection do Qdrant muito grande | Busca lenta | Monitorar tamanho; particionar se > 100k vetores por tenant |
| Tenant esquece de ser setado em nova feature | Data leak silencioso | Testes de integração obrigatórios; middleware rejeita requests sem tenant |
| Migration complexa dos dados existentes | Downtime | Script de migração que atribui dados existentes a um tenant default |

---

## Checklist de Migração (dados existentes)

```python
# scripts/migrate_to_multi_tenant.py

"""
1. Criar tenant "default" para o escritório atual
2. UPDATE processos SET tenant_id = 'default-tenant-uuid' WHERE tenant_id IS NULL
3. UPDATE publicacoes SET tenant_id = 'default-tenant-uuid' WHERE tenant_id IS NULL
4. ... repetir para todas as tabelas
5. ALTER TABLE processos ALTER COLUMN tenant_id SET NOT NULL
6. Criar collection 'dje_default_tenant' no Qdrant
7. Migrar vetores existentes para a nova collection
8. Habilitar RLS
9. Validar que tudo funciona com o tenant default
"""
```

---

## Decisões Futuras (fora do escopo atual)

- **Autenticação por tenant**: quando/se precisar de login, considerar Keycloak ou Auth0 com `tenant_id` no token JWT
- **Billing/Quotas**: limitar processos monitorados por plano
- **Tenant dedicado**: para clientes enterprise, extrair para instância separada via Docker Compose override
- **Multi-região**: se tenants em estados diferentes precisarem de latência menor