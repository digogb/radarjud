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
_collections_ready = False

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
    """Cria collections e índices no Qdrant se não existirem. Usa cache para evitar chamadas repetidas."""
    global _collections_ready
    if _collections_ready:
        return

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

    _collections_ready = True


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


def index_publicacoes_batch(items: list, batch_size: int = 32) -> int:
    """Vetoriza e indexa um batch de publicações no Qdrant.

    Args:
        items: lista de tuplas (pub_id: int, pub: dict)
        batch_size: tamanho do batch para o modelo de embedding

    Returns:
        Número de publicações indexadas.
    """
    from qdrant_client.models import PointStruct

    cfg = _get_config()
    model = get_model()
    client = get_client()

    # Filtrar itens com texto válido
    valid = [
        (pub_id, pub, build_publicacao_text(pub))
        for pub_id, pub in items
    ]
    valid = [(pub_id, pub, text) for pub_id, pub, text in valid if text and len(text) >= 20]

    if not valid:
        return 0

    texts = [f"search_document: {text}" for _, _, text in valid]
    vectors = model.encode(texts, normalize_embeddings=True, batch_size=batch_size)

    points = [
        PointStruct(
            id=pub_id,
            vector=vectors[i][: cfg.embedding_dims].tolist(),
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
        for i, (pub_id, pub, text) in enumerate(valid)
    ]

    client.upsert(collection_name=COLLECTION_PUBLICACOES, points=points)
    logger.debug(f"Batch de {len(points)} publicações indexado no Qdrant.")
    return len(points)


def index_processos_batch(processos: list, batch_size: int = 32) -> int:
    """Vetoriza e indexa um batch de processos no Qdrant.

    Args:
        processos: lista de dicts com chaves numero_processo, tribunal, publicacoes
        batch_size: tamanho do batch para o modelo de embedding

    Returns:
        Número de processos indexados.
    """
    from qdrant_client.models import PointStruct

    cfg = _get_config()
    model = get_model()
    client = get_client()

    valid = [
        (proc, build_processo_text(proc))
        for proc in processos
    ]
    valid = [(proc, text) for proc, text in valid if text and len(text) >= 20]

    if not valid:
        return 0

    texts = [f"search_document: {text}" for _, text in valid]
    vectors = model.encode(texts, normalize_embeddings=True, batch_size=batch_size)

    points = [
        PointStruct(
            id=abs(hash(proc.get("numero_processo", ""))) % (2**63),
            vector=vectors[i][: cfg.embedding_dims].tolist(),
            payload={
                "numero_processo": proc.get("numero_processo"),
                "tribunal": proc.get("tribunal"),
                "total_publicacoes": len(proc.get("publicacoes", [])),
                "texto_resumo": text[:500],
            },
        )
        for i, (proc, text) in enumerate(valid)
    ]

    client.upsert(collection_name=COLLECTION_PROCESSOS, points=points)
    logger.debug(f"Batch de {len(points)} processos indexado no Qdrant.")
    return len(points)


def _log_score_stats(label: str, scores: list[float], threshold: float) -> None:
    """Loga distribuição de scores para análise de qualidade."""
    if not scores:
        logger.info(f"[SEMANTIC] {label}: 0 resultados (threshold={threshold:.2f})")
        return
    buckets = {">=0.8": 0, "0.6-0.8": 0, "0.5-0.6": 0, "0.4-0.5": 0, "<0.4": 0}
    for s in scores:
        if s >= 0.8:
            buckets[">=0.8"] += 1
        elif s >= 0.6:
            buckets["0.6-0.8"] += 1
        elif s >= 0.5:
            buckets["0.5-0.6"] += 1
        elif s >= 0.4:
            buckets["0.4-0.5"] += 1
        else:
            buckets["<0.4"] += 1
    dist = " | ".join(f"{k}:{v}" for k, v in buckets.items() if v > 0)
    logger.info(
        f"[SEMANTIC] {label}: {len(scores)} resultado(s) | "
        f"threshold={threshold:.2f} | min={min(scores):.4f} max={max(scores):.4f} "
        f"avg={sum(scores)/len(scores):.4f} | dist=[{dist}]"
    )


# Query fixa que representa o conceito de "oportunidade de crédito" no DJe
QUERY_OPORTUNIDADE_CREDITO = (
    "alvará de levantamento de depósito judicial pagamento de crédito "
    "recebimento de valores mandado de levantamento precatório execução "
    "requisição de pequeno valor RPV acordo homologado desbloqueio ordem de pagamento"
)


def rerank_oportunidades(pub_ids: list, threshold: float = 0.45) -> dict:
    """Pontua semanticamente candidatos a oportunidade de crédito pré-filtrados por keyword.

    Usa Qdrant para buscar similaridade entre os pub_ids e a query canônica de oportunidade.
    Retorna apenas os IDs cujo score está acima do threshold.

    Em caso de erro (Qdrant indisponível, pub não indexado), retorna todos os candidatos
    sem filtrar (fail-safe: melhor falso positivo que falso negativo).

    Returns:
        Dict {pub_id: score} para os aprovados.
    """
    if not pub_ids:
        return {}

    try:
        from qdrant_client.models import Filter, HasIdCondition

        vector = encode(QUERY_OPORTUNIDADE_CREDITO, prefix="search_query")
        client = get_client()

        results = client.query_points(
            collection_name=COLLECTION_PUBLICACOES,
            query=vector,
            query_filter=Filter(must=[HasIdCondition(has_id=list(pub_ids))]),
            limit=len(pub_ids),
            score_threshold=threshold,
        )

        scores = {r.id: round(r.score, 4) for r in results.points}
        all_scores = list(scores.values())
        _log_score_stats(f"rerank_oportunidades ({len(pub_ids)} candidatos)", all_scores, threshold)
        return scores

    except Exception as e:
        logger.warning(
            f"rerank_oportunidades: erro no Qdrant, retornando todos os candidatos sem filtrar. {e}"
        )
        # Fail-safe: não descartar oportunidades por falha de infraestrutura
        return {pub_id: 0.0 for pub_id in pub_ids}


def search_publicacoes(
    query: str,
    tribunal: Optional[str] = None,
    pessoa_id: Optional[int] = None,
    limit: Optional[int] = None,
    score_threshold: Optional[float] = None,
) -> list:
    """Busca semântica em publicações com filtros opcionais."""
    import time
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    cfg = _get_config()
    limit = limit or cfg.semantic_max_results
    score_threshold = score_threshold if score_threshold is not None else cfg.semantic_score_threshold

    t0 = time.perf_counter()
    vector = encode(query, prefix="search_query")
    t_encode = time.perf_counter() - t0

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

    t1 = time.perf_counter()
    results = client.query_points(
        collection_name=COLLECTION_PUBLICACOES,
        query=vector,
        query_filter=query_filter,
        limit=limit,
        score_threshold=score_threshold,
    )
    t_qdrant = time.perf_counter() - t1

    scores = [round(r.score, 4) for r in results.points]
    filters_str = " ".join(filter(None, [tribunal, f"pessoa={pessoa_id}" if pessoa_id else None]))
    logger.info(
        f"[SEMANTIC:publicacoes] query={repr(query[:60])} filtros=[{filters_str}] "
        f"encode={t_encode*1000:.0f}ms qdrant={t_qdrant*1000:.0f}ms"
    )
    _log_score_stats("publicacoes", scores, score_threshold)

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
    import time
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    cfg = _get_config()
    limit = limit or cfg.semantic_max_results
    score_threshold = score_threshold if score_threshold is not None else cfg.semantic_score_threshold_processos

    t0 = time.perf_counter()
    vector = encode(query, prefix="search_query")
    t_encode = time.perf_counter() - t0

    client = get_client()

    query_filter = None
    if tribunal:
        query_filter = Filter(
            must=[FieldCondition(key="tribunal", match=MatchValue(value=tribunal))]
        )

    t1 = time.perf_counter()
    results = client.query_points(
        collection_name=COLLECTION_PROCESSOS,
        query=vector,
        query_filter=query_filter,
        limit=limit,
        score_threshold=score_threshold,
    )
    t_qdrant = time.perf_counter() - t1

    scores = [round(r.score, 4) for r in results.points]
    logger.info(
        f"[SEMANTIC:processos] query={repr(query[:60])} filtros=[{tribunal or ''}] "
        f"encode={t_encode*1000:.0f}ms qdrant={t_qdrant*1000:.0f}ms"
    )
    _log_score_stats("processos", scores, score_threshold)

    return [
        {
            "processo_id": r.id,
            "score": round(r.score, 4),
            **(r.payload or {}),
        }
        for r in results.points
    ]
