"""
Serviço de Embedding Semântico.

Responsável por:
- Gerenciar conexão com Qdrant
- Carregar modelo Nomic (lazy loading / singleton)
- Criar collections com índices
- Montar texto concatenado para embedding
- Indexar publicação (encode + upsert)
- Busca semântica (encode query + search + filtros)
"""

import json
import logging
import os
import sys

from typing import Optional

logger = logging.getLogger(__name__)

# Singleton para evitar recarregar modelo a cada task
_model = None
_client = None

COLLECTION_PUBLICACOES = "publicacoes"
COLLECTION_PROCESSOS = "processos"


def _get_config():
    """Carrega config dinamicamente para evitar import circular."""
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import Config
    return Config()


def get_model():
    """Retorna modelo Nomic (singleton, carregado na primeira chamada)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        cfg = _get_config()
        logger.info(f"Carregando modelo {cfg.embedding_model}...")
        _model = SentenceTransformer(cfg.embedding_model, trust_remote_code=True)
        logger.info("Modelo carregado.")
    return _model


def get_client():
    """Retorna cliente Qdrant (singleton)."""
    global _client
    if _client is None:
        from qdrant_client import QdrantClient
        cfg = _get_config()
        _client = QdrantClient(url=cfg.qdrant_url, timeout=30)
    return _client


def ensure_collections():
    """Cria collections e índices no Qdrant se não existirem."""
    from qdrant_client.models import (
        Distance, VectorParams, PayloadSchemaType
    )
    cfg = _get_config()
    client = get_client()
    existing = [c.name for c in client.get_collections().collections]

    for collection in [COLLECTION_PUBLICACOES, COLLECTION_PROCESSOS]:
        if collection not in existing:
            client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(
                    size=cfg.embedding_dims,
                    distance=Distance.COSINE,
                ),
            )
            client.create_payload_index(collection, "tribunal", PayloadSchemaType.KEYWORD)
            client.create_payload_index(collection, "pessoa_id", PayloadSchemaType.INTEGER)
            client.create_payload_index(collection, "numero_processo", PayloadSchemaType.KEYWORD)
            client.create_payload_index(collection, "data_disponibilizacao", PayloadSchemaType.KEYWORD)
            logger.info(f"Collection '{collection}' criada com índices.")


def build_publicacao_text(pub: dict) -> str:
    """Concatena campos relevantes da publicação para gerar embedding rico."""
    # Extrair polos do JSON (suporta polos_json string, polos dict, polo_ativo/polo_passivo direto)
    polo_ativo = pub.get("polo_ativo", "")
    polo_passivo = pub.get("polo_passivo", "")

    if not polo_ativo and not polo_passivo:
        polos_raw = pub.get("polos_json") or pub.get("polos", {})
        if isinstance(polos_raw, str):
            try:
                polos = json.loads(polos_raw)
                polo_ativo = ", ".join(polos.get("ativo", []))
                polo_passivo = ", ".join(polos.get("passivo", []))
            except (json.JSONDecodeError, AttributeError):
                pass
        elif isinstance(polos_raw, dict):
            polo_ativo = ", ".join(polos_raw.get("ativo", []))
            polo_passivo = ", ".join(polos_raw.get("passivo", []))

    # Texto principal — preferir texto_completo, fallback para texto_resumo
    texto = (
        pub.get("texto_completo")
        or pub.get("texto_publicacao")
        or pub.get("texto_resumo")
        or pub.get("texto", "")
    )

    fields = [
        texto,
        f"Polo Ativo: {polo_ativo}" if polo_ativo else "",
        f"Polo Passivo: {polo_passivo}" if polo_passivo else "",
        f"Órgão: {pub.get('orgao', '')}" if pub.get("orgao") else "",
        f"Tipo: {pub.get('tipo_comunicacao', '')}" if pub.get("tipo_comunicacao") else "",
        f"Processo: {pub.get('numero_processo', '')}" if pub.get("numero_processo") else "",
    ]
    return " ".join(f for f in fields if f).strip()


def build_processo_text(processo: dict) -> str:
    """Concatena histórico de publicações de um processo em texto único."""
    parts = [
        f"Processo: {processo.get('numero_processo', '')}",
        f"Tribunal: {processo.get('tribunal', '')}",
    ]
    for pub in processo.get("publicacoes", []):
        texto = pub.get("texto_completo") or pub.get("texto_publicacao") or pub.get("texto_resumo") or ""
        if texto:
            parts.append(texto)
    return " ".join(p for p in parts if p).strip()


def encode(text: str, prefix: str = "search_document") -> list:
    """Gera embedding com prefixo Nomic e truncamento Matryoshka."""
    cfg = _get_config()
    model = get_model()
    full_text = f"{prefix}: {text}"
    vector = model.encode(full_text, normalize_embeddings=True).tolist()
    return vector[: cfg.embedding_dims]


def index_publicacao(pub_id: int, pub: dict):
    """Vetoriza e indexa uma publicação no Qdrant."""
    from qdrant_client.models import PointStruct

    text = build_publicacao_text(pub)
    if not text or len(text) < 20:
        logger.debug(f"Publicação {pub_id}: texto muito curto, pulando.")
        return

    vector = encode(text, prefix="search_document")
    client = get_client()

    client.upsert(
        collection_name=COLLECTION_PUBLICACOES,
        points=[
            PointStruct(
                id=pub_id,
                vector=vector,
                payload={
                    "pessoa_id": pub.get("pessoa_id"),
                    "tribunal": pub.get("tribunal"),
                    "numero_processo": pub.get("numero_processo"),
                    "data_disponibilizacao": pub.get("data_disponibilizacao") or pub.get("data_publicacao"),
                    "polo_ativo": _extract_polo(pub, "ativo")[:200],
                    "polo_passivo": _extract_polo(pub, "passivo")[:200],
                    "orgao": (pub.get("orgao") or "")[:200],
                    "tipo_comunicacao": (pub.get("tipo_comunicacao") or "")[:100],
                    "texto_resumo": text[:500],
                },
            )
        ],
    )
    logger.debug(f"Publicação {pub_id} indexada no Qdrant.")


def _extract_polo(pub: dict, polo: str) -> str:
    """Extrai polo ativo ou passivo de um dict de publicação."""
    direct_key = f"polo_{polo}"
    if pub.get(direct_key):
        return pub[direct_key]

    polos_raw = pub.get("polos_json") or pub.get("polos", {})
    if isinstance(polos_raw, str):
        try:
            polos = json.loads(polos_raw)
            return ", ".join(polos.get(polo, []))
        except (json.JSONDecodeError, AttributeError):
            return ""
    elif isinstance(polos_raw, dict):
        return ", ".join(polos_raw.get(polo, []))
    return ""


def index_processo(processo_id: str, processo: dict):
    """Vetoriza histórico concatenado de um processo."""
    from qdrant_client.models import PointStruct

    text = build_processo_text(processo)
    if not text or len(text) < 20:
        return

    vector = encode(text, prefix="search_document")
    client = get_client()

    # Usa hash do numero_processo como ID numérico
    point_id = abs(hash(processo_id)) % (2**63)

    client.upsert(
        collection_name=COLLECTION_PROCESSOS,
        points=[
            PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "numero_processo": processo.get("numero_processo"),
                    "tribunal": processo.get("tribunal"),
                    "total_publicacoes": len(processo.get("publicacoes", [])),
                    "texto_resumo": text[:500],
                },
            )
        ],
    )
    logger.debug(f"Processo {processo_id} indexado no Qdrant.")


def search_publicacoes(
    query: str,
    tribunal: Optional[str] = None,
    pessoa_id: Optional[int] = None,
    limit: Optional[int] = None,
    score_threshold: Optional[float] = None,
) -> list:
    """Busca semântica em publicações com filtros opcionais."""
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    cfg = _get_config()
    limit = limit or cfg.semantic_max_results
    score_threshold = score_threshold if score_threshold is not None else cfg.semantic_score_threshold

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

    results = client.query_points(
        collection_name=COLLECTION_PUBLICACOES,
        query=vector,
        query_filter=query_filter,
        limit=limit,
        score_threshold=score_threshold,
    )

    return [
        {
            "pub_id": r.id,
            "score": round(r.score, 4),
            **(r.payload or {}),
        }
        for r in results.points
    ]


def search_processos(
    query: str,
    tribunal: Optional[str] = None,
    limit: Optional[int] = None,
    score_threshold: Optional[float] = None,
) -> list:
    """Busca semântica em processos (histórico concatenado)."""
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    cfg = _get_config()
    limit = limit or cfg.semantic_max_results
    score_threshold = score_threshold if score_threshold is not None else cfg.semantic_score_threshold_processos

    vector = encode(query, prefix="search_query")
    client = get_client()

    query_filter = None
    if tribunal:
        query_filter = Filter(
            must=[FieldCondition(key="tribunal", match=MatchValue(value=tribunal))]
        )

    results = client.query_points(
        collection_name=COLLECTION_PROCESSOS,
        query=vector,
        query_filter=query_filter,
        limit=limit,
        score_threshold=score_threshold,
    )

    return [
        {
            "processo_id": r.id,
            "score": round(r.score, 4),
            **(r.payload or {}),
        }
        for r in results.points
    ]
