# Plano de Implementação — Busca Semântica no DJE Monitor

## 1. Visão Geral

### Objetivo
Adicionar busca semântica ao DJE Monitor para permitir que o escritório encontre publicações e processos relevantes por similaridade de contexto jurídico, indo além das buscas textuais exatas. Exemplo: buscar "execução fiscal dívida tributária IPTU" e encontrar publicações semanticamente relacionadas mesmo que não contenham exatamente essas palavras.

### Stack da Feature
| Componente | Tecnologia | Justificativa |
|---|---|---|
| Modelo de Embedding | `nomic-ai/nomic-embed-text-v1.5` | Contexto de 8192 tokens (textos jurídicos longos), Matryoshka (dims flexíveis), multilingual, Apache 2.0 |
| Vector Store | Qdrant | Container Docker, filtros híbridos (metadata + semântica), API REST + Python client, persistência em disco |
| Task Queue | Dramatiq (existente) | Nova fila `indexacao` para vetorização assíncrona |
| Similaridade | Cosseno (default Qdrant) | Padrão para text embeddings normalizados |

### Arquitetura de Alto Nível
```
┌──────────────────────────────────────────────────────────────────┐
│ FLUXO DE INDEXAÇÃO (background)                                  │
│                                                                  │
│  Nova Publicação (Postgres)                                      │
│       │                                                          │
│       ▼                                                          │
│  indexar_publicacao_task.send()                                   │
│       │                                                          │
│       ▼                                                          │
│  Worker Dramatiq (fila: indexacao)                                │
│       │                                                          │
│       ├── Concatena campos textuais                              │
│       ├── Nomic encode("search_document: ...")                   │
│       ├── Trunca vetor → 256 dims (Matryoshka)                  │
│       └── Qdrant upsert(id, vector, payload)                    │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ FLUXO DE BUSCA (request-time)                                    │
│                                                                  │
│  Usuário: "execução fiscal dívida tributária"                    │
│       │                                                          │
│       ▼                                                          │
│  GET /api/v1/search/semantic?q=...&tribunal=TJCE                 │
│       │                                                          │
│       ├── Nomic encode("search_query: ...")                      │
│       ├── Qdrant search(vector, filter=tribunal, top_k=20)      │
│       └── Retorna publicações rankeadas por score                │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Pré-requisitos

### 2.1 Dependências Python
```
# Adicionar ao requirements.txt
sentence-transformers>=2.7.0
qdrant-client>=1.9.0
torch>=2.0.0   # CPU-only é suficiente
```

> **Nota sobre torch:** Para manter a imagem Docker leve, usar a versão CPU-only:
> `pip install torch --index-url https://download.pytorch.org/whl/cpu`

### 2.2 Container Qdrant
Adicionar ao `docker-compose.yml` (Fase 1, passo 1).

### 2.3 Variáveis de Ambiente
```env
# Adicionar ao .env.example
DJE_QDRANT_URL=http://qdrant:6333
DJE_EMBEDDING_MODEL=nomic-ai/nomic-embed-text-v1.5
DJE_EMBEDDING_DIMS=256          # Matryoshka: 256, 512 ou 768
DJE_SEMANTIC_SCORE_THRESHOLD=0.35
DJE_SEMANTIC_MAX_RESULTS=20
```

### 2.4 Espaço em Disco
- Modelo Nomic: ~550MB (download no primeiro boot do worker)
- Qdrant: ~1KB por vetor (256 dims × float32). Para 100k publicações ≈ 100MB.

---

## 3. Fases de Implementação

---

### FASE 1 — Infraestrutura e Serviço de Embedding
**Duração estimada: 2-3 dias**

#### Passo 1.1 — Qdrant no Docker Compose

Arquivo: `docker-compose.yml`

```yaml
qdrant:
  image: qdrant/qdrant:v1.9.7
  ports:
    - "6333:6333"
    - "6334:6334"   # gRPC (opcional, melhor performance)
  volumes:
    - qdrant_data:/qdrant/storage
  environment:
    QDRANT__SERVICE__GRPC_PORT: 6334
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:6333/healthz"]
    interval: 10s
    timeout: 5s
    retries: 5
  restart: unless-stopped
```

Adicionar `qdrant_data` ao bloco `volumes` e `depends_on: qdrant` nos serviços `api` e `worker`.

**Critério de aceite:** `curl http://localhost:6333/healthz` retorna `200`.

---

#### Passo 1.2 — Configuração

Arquivo: `src/config.py` — adicionar:

```python
# Semantic Search
QDRANT_URL: str = os.getenv("DJE_QDRANT_URL", "http://qdrant:6333")
EMBEDDING_MODEL: str = os.getenv("DJE_EMBEDDING_MODEL", "nomic-ai/nomic-embed-text-v1.5")
EMBEDDING_DIMS: int = int(os.getenv("DJE_EMBEDDING_DIMS", "256"))
SEMANTIC_SCORE_THRESHOLD: float = float(os.getenv("DJE_SEMANTIC_SCORE_THRESHOLD", "0.35"))
SEMANTIC_MAX_RESULTS: int = int(os.getenv("DJE_SEMANTIC_MAX_RESULTS", "20"))
```

---

#### Passo 1.3 — Serviço de Embedding (core)

Arquivo: `src/services/embedding_service.py`

**Responsabilidades:**
- Gerenciar conexão com Qdrant
- Carregar modelo Nomic (lazy loading / singleton)
- Criar collection com índices
- Montar texto concatenado para embedding
- Indexar publicação (encode + upsert)
- Busca semântica (encode query + search + filtros)

**Implementação detalhada:**

```python
import logging
from typing import Optional
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue,
    PayloadSchemaType
)
from config import (
    QDRANT_URL, EMBEDDING_MODEL, EMBEDDING_DIMS,
    SEMANTIC_SCORE_THRESHOLD, SEMANTIC_MAX_RESULTS
)

logger = logging.getLogger(__name__)

# Singleton para evitar recarregar modelo a cada task
_model: Optional[SentenceTransformer] = None
_client: Optional[QdrantClient] = None

COLLECTION_PUBLICACOES = "publicacoes"
COLLECTION_PROCESSOS = "processos"


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info(f"Carregando modelo {EMBEDDING_MODEL}...")
        _model = SentenceTransformer(EMBEDDING_MODEL, trust_remote_code=True)
        logger.info("Modelo carregado.")
    return _model


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=QDRANT_URL, timeout=30)
    return _client


def ensure_collections():
    """Cria collections e índices no Qdrant se não existirem."""
    client = get_client()
    existing = [c.name for c in client.get_collections().collections]

    for collection in [COLLECTION_PUBLICACOES, COLLECTION_PROCESSOS]:
        if collection not in existing:
            client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIMS,
                    distance=Distance.COSINE,
                ),
            )
            # Índices para filtro híbrido
            client.create_payload_index(collection, "tribunal", PayloadSchemaType.KEYWORD)
            client.create_payload_index(collection, "pessoa_id", PayloadSchemaType.INTEGER)
            client.create_payload_index(collection, "numero_processo", PayloadSchemaType.KEYWORD)
            client.create_payload_index(collection, "data_publicacao", PayloadSchemaType.KEYWORD)
            logger.info(f"Collection '{collection}' criada com índices.")


def build_publicacao_text(pub: dict) -> str:
    """Concatena campos relevantes da publicação para gerar embedding rico."""
    fields = [
        pub.get("texto_publicacao", ""),
        f"Polo Ativo: {pub.get('polo_ativo', '')}",
        f"Polo Passivo: {pub.get('polo_passivo', '')}",
        f"Órgão: {pub.get('orgao', '')}",
        f"Tipo: {pub.get('tipo_comunicacao', '')}",
        f"Processo: {pub.get('numero_processo', '')}",
    ]
    return " ".join(f for f in fields if f and f.split(": ", 1)[-1]).strip()


def build_processo_text(processo: dict) -> str:
    """Concatena histórico de publicações de um processo em texto único."""
    parts = [
        f"Processo: {processo.get('numero_processo', '')}",
        f"Tribunal: {processo.get('tribunal', '')}",
    ]
    for pub in processo.get("publicacoes", []):
        parts.append(pub.get("texto_publicacao", ""))
    return " ".join(p for p in parts if p).strip()


def encode(text: str, prefix: str = "search_document") -> list[float]:
    """Gera embedding com prefixo Nomic e truncamento Matryoshka."""
    model = get_model()
    full_text = f"{prefix}: {text}"
    vector = model.encode(full_text, normalize_embeddings=True).tolist()
    return vector[:EMBEDDING_DIMS]


def index_publicacao(pub_id: int, pub: dict):
    """Vetoriza e indexa uma publicação no Qdrant."""
    text = build_publicacao_text(pub)
    if not text or len(text) < 20:
        logger.debug(f"Publicação {pub_id}: texto muito curto, pulando.")
        return

    vector = encode(text, prefix="search_document")
    client = get_client()

    client.upsert(
        collection_name=COLLECTION_PUBLICACOES,
        points=[PointStruct(
            id=pub_id,
            vector=vector,
            payload={
                "pessoa_id": pub.get("pessoa_id"),
                "tribunal": pub.get("tribunal"),
                "numero_processo": pub.get("numero_processo"),
                "data_publicacao": pub.get("data_publicacao"),
                "polo_ativo": pub.get("polo_ativo", "")[:200],
                "polo_passivo": pub.get("polo_passivo", "")[:200],
                "orgao": pub.get("orgao", "")[:200],
                "tipo_comunicacao": pub.get("tipo_comunicacao", "")[:100],
                "texto_resumo": text[:500],
            },
        )],
    )
    logger.debug(f"Publicação {pub_id} indexada no Qdrant.")


def index_processo(processo_id: str, processo: dict):
    """Vetoriza histórico concatenado de um processo."""
    text = build_processo_text(processo)
    if not text or len(text) < 20:
        return

    vector = encode(text, prefix="search_document")
    client = get_client()

    # Usa hash do numero_processo como ID numérico
    point_id = abs(hash(processo_id)) % (2**63)

    client.upsert(
        collection_name=COLLECTION_PROCESSOS,
        points=[PointStruct(
            id=point_id,
            vector=vector,
            payload={
                "numero_processo": processo.get("numero_processo"),
                "tribunal": processo.get("tribunal"),
                "total_publicacoes": len(processo.get("publicacoes", [])),
                "texto_resumo": text[:500],
            },
        )],
    )


def search_publicacoes(
    query: str,
    tribunal: str | None = None,
    pessoa_id: int | None = None,
    limit: int = SEMANTIC_MAX_RESULTS,
    score_threshold: float = SEMANTIC_SCORE_THRESHOLD,
) -> list[dict]:
    """Busca semântica em publicações com filtros opcionais."""
    vector = encode(query, prefix="search_query")
    client = get_client()

    must_conditions = []
    if tribunal:
        must_conditions.append(
            FieldCondition(key="tribunal", match=MatchValue(value=tribunal))
        )
    if pessoa_id:
        must_conditions.append(
            FieldCondition(key="pessoa_id", match=MatchValue(value=pessoa_id))
        )

    query_filter = Filter(must=must_conditions) if must_conditions else None

    results = client.search(
        collection_name=COLLECTION_PUBLICACOES,
        query_vector=vector,
        query_filter=query_filter,
        limit=limit,
        score_threshold=score_threshold,
    )

    return [
        {
            "pub_id": r.id,
            "score": round(r.score, 4),
            **r.payload,
        }
        for r in results
    ]


def search_processos(
    query: str,
    tribunal: str | None = None,
    limit: int = SEMANTIC_MAX_RESULTS,
    score_threshold: float = SEMANTIC_SCORE_THRESHOLD,
) -> list[dict]:
    """Busca semântica em processos (histórico concatenado)."""
    vector = encode(query, prefix="search_query")
    client = get_client()

    query_filter = None
    if tribunal:
        query_filter = Filter(must=[
            FieldCondition(key="tribunal", match=MatchValue(value=tribunal))
        ])

    results = client.search(
        collection_name=COLLECTION_PROCESSOS,
        query_vector=vector,
        query_filter=query_filter,
        limit=limit,
        score_threshold=score_threshold,
    )

    return [
        {
            "processo_id": r.id,
            "score": round(r.score, 4),
            **r.payload,
        }
        for r in results
    ]
```

**Critérios de aceite:**
- `ensure_collections()` cria as collections `publicacoes` e `processos` no Qdrant
- `encode()` retorna vetor de `EMBEDDING_DIMS` dimensões
- `index_publicacao()` faz upsert sem erro
- `search_publicacoes()` retorna resultados ordenados por score

---

### FASE 2 — Tasks Dramatiq de Indexação
**Duração estimada: 1-2 dias**

#### Passo 2.1 — Tasks de Indexação

Arquivo: `src/tasks.py` — adicionar:

```python
# ============================================================
# FILA: indexacao — Vetorização para busca semântica
# ============================================================

@dramatiq.actor(queue_name="indexacao", max_retries=3, min_backoff=5000)
def indexar_publicacao_task(pub_id: int, pub_data: dict):
    """Vetoriza uma publicação individual."""
    from services.embedding_service import index_publicacao, ensure_collections
    ensure_collections()
    index_publicacao(pub_id, pub_data)


@dramatiq.actor(queue_name="indexacao", max_retries=3, min_backoff=5000)
def indexar_processo_task(processo_id: str, processo_data: dict):
    """Vetoriza histórico concatenado de um processo."""
    from services.embedding_service import index_processo, ensure_collections
    ensure_collections()
    index_processo(processo_id, processo_data)


@dramatiq.actor(queue_name="indexacao", max_retries=1)
def reindexar_tudo_task():
    """Backfill: reindexar todas as publicações existentes no Qdrant.
    Processa em batches para não sobrecarregar memória.
    """
    from services.embedding_service import (
        ensure_collections, index_publicacao, get_client
    )
    from storage.repository import get_publicacoes_batch

    ensure_collections()

    offset = 0
    batch_size = 100
    total = 0

    while True:
        pubs = get_publicacoes_batch(offset=offset, limit=batch_size)
        if not pubs:
            break
        for pub in pubs:
            try:
                index_publicacao(pub.id, pub.to_dict())
                total += 1
            except Exception as e:
                logger.error(f"Erro indexando pub {pub.id}: {e}")
        offset += batch_size
        logger.info(f"Reindex: {total} publicações processadas...")

    logger.info(f"Reindex completo: {total} publicações indexadas.")
```

---

#### Passo 2.2 — Hook no Fluxo Existente

Arquivo: `src/services/monitor_service.py` — após salvar publicação:

```python
# ANTES (existente):
# pub = salvar_publicacao(...)
# criar_alerta(pub)

# DEPOIS (adicionar):
from tasks import indexar_publicacao_task

pub = salvar_publicacao(...)
criar_alerta(pub)

# Enfileira vetorização assíncrona
indexar_publicacao_task.send(pub.id, pub.to_dict())
```

**Importante:** O `to_dict()` do model precisa retornar os campos necessários:
- `texto_publicacao`, `polo_ativo`, `polo_passivo`, `orgao`
- `tipo_comunicacao`, `numero_processo`, `tribunal`
- `pessoa_id`, `data_publicacao`

Verificar se já existe ou adicionar ao model.

---

#### Passo 2.3 — Startup da Collection

Arquivo: `src/api.py` — no startup:

```python
@app.on_event("startup")
async def startup():
    # ... código existente ...

    # Garantir collections do Qdrant
    try:
        from services.embedding_service import ensure_collections
        ensure_collections()
        logger.info("Qdrant collections verificadas.")
    except Exception as e:
        logger.warning(f"Qdrant indisponível no startup: {e}")
```

**Critérios de aceite:**
- Nova publicação salva → aparece no Qdrant em segundos
- `reindexar_tudo_task` processa todas as publicações existentes
- Worker não quebra se Qdrant estiver indisponível (retry com backoff)

---

### FASE 3 — Endpoints da API
**Duração estimada: 1 dia**

#### Passo 3.1 — Endpoint de Busca Semântica

Arquivo: `src/api.py` — adicionar:

```python
from pydantic import BaseModel
from typing import Optional

class SemanticSearchResult(BaseModel):
    pub_id: int
    score: float
    tribunal: Optional[str] = None
    numero_processo: Optional[str] = None
    data_publicacao: Optional[str] = None
    polo_ativo: Optional[str] = None
    polo_passivo: Optional[str] = None
    orgao: Optional[str] = None
    tipo_comunicacao: Optional[str] = None
    texto_resumo: Optional[str] = None

class ProcessoSearchResult(BaseModel):
    processo_id: int
    score: float
    numero_processo: Optional[str] = None
    tribunal: Optional[str] = None
    total_publicacoes: Optional[int] = None
    texto_resumo: Optional[str] = None


@app.get("/api/v1/search/semantic", response_model=dict)
def semantic_search(
    q: str,
    tribunal: str | None = None,
    pessoa_id: int | None = None,
    limit: int = Query(20, ge=1, le=100),
    score_threshold: float = Query(0.35, ge=0.0, le=1.0),
    tipo: str = Query("publicacoes", regex="^(publicacoes|processos)$"),
):
    """
    Busca semântica em publicações ou processos.

    - **q**: Texto da busca (ex: "execução fiscal dívida tributária")
    - **tribunal**: Filtro por tribunal (ex: TJCE)
    - **pessoa_id**: Filtro por pessoa monitorada
    - **limit**: Máximo de resultados (1-100)
    - **score_threshold**: Score mínimo de similaridade (0.0-1.0)
    - **tipo**: "publicacoes" ou "processos"
    """
    from services.embedding_service import search_publicacoes, search_processos

    if tipo == "processos":
        results = search_processos(
            query=q, tribunal=tribunal,
            limit=limit, score_threshold=score_threshold,
        )
    else:
        results = search_publicacoes(
            query=q, tribunal=tribunal, pessoa_id=pessoa_id,
            limit=limit, score_threshold=score_threshold,
        )

    return {
        "query": q,
        "tipo": tipo,
        "total": len(results),
        "results": results,
    }


@app.post("/api/v1/search/reindex")
def trigger_reindex():
    """Dispara reindexação completa das publicações no Qdrant."""
    from tasks import reindexar_tudo_task
    reindexar_tudo_task.send()
    return {"status": "reindex enfileirado"}


@app.get("/api/v1/search/semantic/status")
def semantic_status():
    """Status do Qdrant e collections."""
    try:
        from services.embedding_service import get_client
        client = get_client()
        collections = {}
        for c in client.get_collections().collections:
            info = client.get_collection(c.name)
            collections[c.name] = {
                "points": info.points_count,
                "vectors": info.vectors_count,
                "status": info.status.value,
            }
        return {"status": "ok", "collections": collections}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

**Critérios de aceite:**
- `GET /api/v1/search/semantic?q=execução fiscal&tribunal=TJCE` retorna publicações rankeadas
- `GET /api/v1/search/semantic?q=dívida tributária&tipo=processos` retorna processos
- `POST /api/v1/search/reindex` enfileira reindex
- `GET /api/v1/search/semantic/status` mostra contadores do Qdrant

---

### FASE 4 — Frontend (React)
**Duração estimada: 2-3 dias**

#### Passo 4.1 — Client HTTP

Arquivo: `web/src/services/api.ts` — adicionar:

```typescript
export interface SemanticResult {
  pub_id: number;
  score: number;
  tribunal?: string;
  numero_processo?: string;
  data_publicacao?: string;
  polo_ativo?: string;
  polo_passivo?: string;
  orgao?: string;
  tipo_comunicacao?: string;
  texto_resumo?: string;
}

export interface SemanticResponse {
  query: string;
  tipo: string;
  total: number;
  results: SemanticResult[];
}

export async function semanticSearch(params: {
  q: string;
  tribunal?: string;
  pessoa_id?: number;
  limit?: number;
  score_threshold?: number;
  tipo?: "publicacoes" | "processos";
}): Promise<SemanticResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set("q", params.q);
  if (params.tribunal) searchParams.set("tribunal", params.tribunal);
  if (params.pessoa_id) searchParams.set("pessoa_id", String(params.pessoa_id));
  if (params.limit) searchParams.set("limit", String(params.limit));
  if (params.score_threshold)
    searchParams.set("score_threshold", String(params.score_threshold));
  if (params.tipo) searchParams.set("tipo", params.tipo);

  const res = await fetch(`/api/v1/search/semantic?${searchParams}`);
  if (!res.ok) throw new Error("Erro na busca semântica");
  return res.json();
}

export async function semanticStatus(): Promise<{
  status: string;
  collections: Record<string, {
    points: number; vectors: number; status: string
  }>;
}> {
  const res = await fetch("/api/v1/search/semantic/status");
  return res.json();
}

export async function triggerReindex(): Promise<{ status: string }> {
  const res = await fetch("/api/v1/search/reindex", { method: "POST" });
  return res.json();
}
```

---

#### Passo 4.2 — Componente de Busca Semântica

Integrar na página `Busca.tsx` existente como uma aba ou toggle:

**UX proposta:**
- Toggle "Busca exata" / "Busca semântica" no topo da busca
- Input de texto livre (sentença natural) em vez de nome/número
- Filtro de tribunal (dropdown, já existe)
- Slider para score mínimo (avançado, colapsável)
- Results como cards com badge de score (0-100%)
- Indicador visual de relevância (barra colorida verde→amarelo→vermelho)
- Click no card → navega para o drawer de detalhe existente

**Wireframe do card de resultado:**
```
┌─────────────────────────────────────────────┐
│ ██████████░░  78% relevância    TJCE        │
│                                             │
│ Processo: 0001234-56.2024.8.06.0001         │
│ Polo Ativo: MUNICÍPIO DE FORTALEZA          │
│ Polo Passivo: JOÃO DA SILVA                 │
│ Órgão: 3ª Vara de Execuções Fiscais         │
│                                             │
│ "...execução fiscal para cobrança de        │
│  crédito tributário relativo ao IPTU..."     │
│                                             │
│ 📅 15/01/2025                    [Ver mais] │
└─────────────────────────────────────────────┘
```

---

#### Passo 4.3 — Widget de Status no Dashboard

Adicionar ao `Dashboard.tsx`:
- Card "Busca Semântica" com total de publicações indexadas
- Status do Qdrant (online/offline)
- Botão "Reindexar" (chama `POST /api/v1/search/reindex`)
- Última reindexação (timestamp)

---

### FASE 5 — Backfill e Reindexação
**Duração estimada: 0.5-1 dia**

#### Passo 5.1 — Script de Backfill

Arquivo: `scripts/backfill_embeddings.py`

```python
"""
Script para indexar publicações existentes no Qdrant.
Pode rodar via CLI ou como task Dramatiq.

Uso:
    python scripts/backfill_embeddings.py
    python scripts/backfill_embeddings.py --batch-size 200 --collection publicacoes
"""
import argparse
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from storage.repository import (
    get_publicacoes_batch,
    get_all_processos_com_publicacoes,
)
from services.embedding_service import (
    ensure_collections, index_publicacao, index_processo
)

def backfill_publicacoes(batch_size: int = 100):
    ensure_collections()
    offset = 0
    total = 0

    while True:
        pubs = get_publicacoes_batch(offset=offset, limit=batch_size)
        if not pubs:
            break
        for pub in pubs:
            try:
                index_publicacao(pub.id, pub.to_dict())
                total += 1
            except Exception as e:
                print(f"ERRO pub {pub.id}: {e}")
        offset += batch_size
        print(f"  → {total} publicações indexadas...")

    print(f"Backfill publicações completo: {total}")

def backfill_processos(batch_size: int = 50):
    ensure_collections()
    processos = get_all_processos_com_publicacoes()
    total = 0

    for proc in processos:
        try:
            index_processo(proc["numero_processo"], proc)
            total += 1
        except Exception as e:
            print(f"ERRO processo {proc.get('numero_processo')}: {e}")

    print(f"Backfill processos completo: {total}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument(
        "--collection",
        choices=["publicacoes", "processos", "all"],
        default="all",
    )
    args = parser.parse_args()

    if args.collection in ("publicacoes", "all"):
        backfill_publicacoes(args.batch_size)
    if args.collection in ("processos", "all"):
        backfill_processos(args.batch_size)
```

#### Passo 5.2 — Repository: funções auxiliares

Arquivo: `src/storage/repository.py` — adicionar:

```python
def get_publicacoes_batch(offset: int = 0, limit: int = 100) -> list:
    """Retorna batch de publicações para reindexação."""
    with get_session() as session:
        return session.query(PublicacaoMonitorada)\
            .order_by(PublicacaoMonitorada.id)\
            .offset(offset)\
            .limit(limit)\
            .all()

def get_all_processos_com_publicacoes() -> list[dict]:
    """Agrupa publicações por numero_processo para indexação de processos."""
    with get_session() as session:
        pubs = session.query(PublicacaoMonitorada)\
            .order_by(PublicacaoMonitorada.numero_processo)\
            .all()

    processos = {}
    for pub in pubs:
        key = pub.numero_processo
        if key not in processos:
            processos[key] = {
                "numero_processo": key,
                "tribunal": pub.tribunal,
                "publicacoes": [],
            }
        processos[key]["publicacoes"].append(pub.to_dict())

    return list(processos.values())
```

---

### FASE 6 — Testes
**Duração estimada: 1-2 dias**

#### Passo 6.1 — Testes unitários do embedding service

Arquivo: `tests/test_embedding_service.py`

```python
import pytest
from unittest.mock import patch, MagicMock


class TestBuildText:
    def test_concatena_campos(self):
        from services.embedding_service import build_publicacao_text
        pub = {
            "texto_publicacao": "Sentença proferida nos autos",
            "polo_ativo": "EMPRESA X",
            "polo_passivo": "JOÃO DA SILVA",
            "orgao": "3ª Vara Cível",
            "tipo_comunicacao": "Intimação",
            "numero_processo": "0001234-56.2024.8.06.0001",
        }
        text = build_publicacao_text(pub)
        assert "Sentença proferida" in text
        assert "EMPRESA X" in text
        assert "JOÃO DA SILVA" in text

    def test_campos_vazios(self):
        from services.embedding_service import build_publicacao_text
        pub = {"texto_publicacao": "Apenas texto"}
        text = build_publicacao_text(pub)
        assert "Apenas texto" in text

    def test_publicacao_vazia(self):
        from services.embedding_service import build_publicacao_text
        text = build_publicacao_text({})
        assert text == ""


class TestEncode:
    @patch("services.embedding_service.get_model")
    def test_retorna_dimensoes_corretas(self, mock_model):
        import numpy as np
        mock_model.return_value.encode.return_value = np.random.rand(768)

        from services.embedding_service import encode
        with patch("services.embedding_service.EMBEDDING_DIMS", 256):
            vector = encode("teste")
            assert len(vector) == 256

    @patch("services.embedding_service.get_model")
    def test_prefixo_search_query(self, mock_model):
        import numpy as np
        mock_model.return_value.encode.return_value = np.random.rand(768)

        from services.embedding_service import encode
        encode("minha busca", prefix="search_query")
        call_args = mock_model.return_value.encode.call_args[0][0]
        assert call_args.startswith("search_query:")


class TestSearch:
    @patch("services.embedding_service.get_client")
    @patch("services.embedding_service.encode")
    def test_search_com_filtro_tribunal(self, mock_encode, mock_client):
        mock_encode.return_value = [0.1] * 256
        mock_result = MagicMock()
        mock_result.id = 1
        mock_result.score = 0.85
        mock_result.payload = {"tribunal": "TJCE", "texto_resumo": "teste"}
        mock_client.return_value.search.return_value = [mock_result]

        from services.embedding_service import search_publicacoes
        results = search_publicacoes("execução fiscal", tribunal="TJCE")

        assert len(results) == 1
        assert results[0]["score"] == 0.85
        # Verifica que filtro foi passado
        call_kwargs = mock_client.return_value.search.call_args[1]
        assert call_kwargs["query_filter"] is not None
```

#### Passo 6.2 — Teste de integração (requer Qdrant rodando)

```python
@pytest.mark.integration
class TestEmbeddingIntegration:
    """Testes que requerem Qdrant e modelo rodando."""

    def test_index_and_search(self):
        from services.embedding_service import (
            ensure_collections, index_publicacao, search_publicacoes
        )
        ensure_collections()

        pub = {
            "texto_publicacao": "Execução fiscal para cobrança de IPTU",
            "polo_ativo": "MUNICÍPIO DE FORTALEZA",
            "polo_passivo": "JOSÉ DA SILVA",
            "orgao": "3ª Vara de Execuções Fiscais",
            "tipo_comunicacao": "Citação",
            "numero_processo": "0001234-56.2024.8.06.0001",
            "tribunal": "TJCE",
            "pessoa_id": 1,
            "data_publicacao": "2024-06-15",
        }
        index_publicacao(99999, pub)

        results = search_publicacoes(
            "dívida tributária IPTU", tribunal="TJCE"
        )
        assert len(results) > 0
        assert results[0]["pub_id"] == 99999
        assert results[0]["score"] > 0.5
```

---

### FASE 7 — Dockerfile e Deploy
**Duração estimada: 0.5-1 dia**

#### Passo 7.1 — Atualizar Dockerfile

```dockerfile
# Adicionar ao Dockerfile existente, no estágio de build:

# torch CPU-only para reduzir tamanho da imagem
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu \
    --break-system-packages
RUN pip install sentence-transformers qdrant-client --break-system-packages

# Pré-download do modelo (evita download no primeiro request)
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('nomic-ai/nomic-embed-text-v1.5', trust_remote_code=True)"
```

> **Nota:** O pré-download do modelo adiciona ~550MB à imagem.
> Se isso for problema, remova a linha e aceite o download no primeiro boot do worker.

#### Passo 7.2 — Docker Compose final

```yaml
# docker-compose.yml — serviços adicionais/modificados
services:
  qdrant:
    image: qdrant/qdrant:v1.9.7
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/healthz"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  api:
    # ... existente ...
    depends_on:
      - postgres
      - redis
      - qdrant    # adicionar
    environment:
      - DJE_QDRANT_URL=http://qdrant:6333
      # ... demais vars existentes ...

  worker:
    # ... existente ...
    depends_on:
      - postgres
      - redis
      - qdrant    # adicionar
    environment:
      - DJE_QDRANT_URL=http://qdrant:6333
      # ... demais vars existentes ...

volumes:
  qdrant_data:    # adicionar
```

---

## 4. Checklist de Validação por Fase

| Fase | Teste de Validação | Comando/Ação |
|---|---|---|
| 1 | Qdrant responde | `curl http://localhost:6333/healthz` |
| 1 | Collections criadas | `curl http://localhost:6333/collections` |
| 1 | Encode funciona | Script Python: `encode("teste")` retorna vetor 256d |
| 2 | Indexação automática | Cadastrar pessoa → first_check → verificar no Qdrant |
| 2 | Reindex funciona | `python scripts/backfill_embeddings.py` |
| 3 | Busca semântica | `GET /api/v1/search/semantic?q=execução fiscal` |
| 3 | Filtro híbrido | `GET /api/v1/search/semantic?q=dívida&tribunal=TJCE` |
| 3 | Status endpoint | `GET /api/v1/search/semantic/status` |
| 4 | UI busca semântica | Toggle funciona, resultados renderizam |
| 4 | Score visual | Badge de % aparece nos cards |
| 5 | Backfill completo | Script roda sem erros, Qdrant mostra points |
| 6 | Testes passam | `pytest tests/test_embedding_service.py` |
| 7 | Docker completo | `docker-compose up -d` sobe todos os 6 serviços |

---

## 5. Cronograma Resumido

| Semana | Fase | Entregas |
|---|---|---|
| **Semana 1** | Fase 1 + 2 | Qdrant rodando, embedding service, tasks Dramatiq, indexação automática |
| **Semana 2** | Fase 3 + 4 | Endpoints API, UI de busca semântica, cards com score |
| **Semana 3** | Fase 5 + 6 + 7 | Backfill, testes, Dockerfile, deploy |

---

## 6. Otimizações Futuras (pós-MVP)

| Otimização | Descrição | Quando |
|---|---|---|
| **Cache de embeddings** | Cachear encode de queries frequentes no Redis | Quando latência da busca > 200ms |
| **Reranking** | Cross-encoder para re-ranquear top-50 → top-10 | Quando qualidade dos resultados não for suficiente |
| **Embeddings de 512 dims** | Subir de 256 → 512 se qualidade estiver baixa | Após análise de recall com dados reais |
| **Busca híbrida** | Combinar BM25 (keyword) + semântica com RRF | Quando keyword exata for importante (ex: número processo) |
| **Atualização incremental de processos** | Re-vetorizar processo quando nova publicação chegar | Fase 2 da feature |
| **GPU** | Adicionar GPU ao worker se volume > 500k publicações | Quando backfill demorar > 2h |
| **Índice HNSW tuning** | Ajustar `m` e `ef_construct` no Qdrant | Quando collection > 1M vetores |
| **Scheduled re-embed** | Re-vetorizar tudo semanalmente (modelo atualizado) | Se trocar modelo |

---

## 7. Riscos e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| Modelo Nomic não entender jargão jurídico PT-BR | Resultados irrelevantes | Testar com 50 queries reais; fallback para `multilingual-e5-base` |
| Imagem Docker muito grande (+2GB com torch) | Deploy lento | Usar torch CPU-only; multi-stage build; pré-download condicional |
| Qdrant fora do ar | Busca semântica indisponível | Graceful degradation: fallback para busca textual; health check |
| Score threshold inadequado | Muitos falsos positivos ou poucos resultados | Threshold configurável via env; UI permite ajuste; começar com 0.35 |
| Publicações com texto curto | Embeddings de baixa qualidade | Filtro mínimo de 20 chars; concatenar mais campos |
| Volume de reindexação alto | Worker sobrecarregado | Fila separada `indexacao`; batch processing; rate limit |