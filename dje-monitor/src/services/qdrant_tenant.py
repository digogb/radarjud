"""
Gerenciamento de collections Qdrant por tenant.

Cada tenant tem 2 collections isoladas:
- dje_{tenant_slug}_publicacoes
- dje_{tenant_slug}_processos

onde tenant_slug é o tenant_id com hífens substituídos por underscores.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

COLLECTION_SUFFIX_PUBLICACOES = "publicacoes"
COLLECTION_SUFFIX_PROCESSOS = "processos"


def _tenant_prefix(tenant_id: str) -> str:
    """Converte UUID para prefixo seguro para nome de collection."""
    return "dje_" + tenant_id.replace("-", "_")


def collection_publicacoes(tenant_id: str) -> str:
    return f"{_tenant_prefix(tenant_id)}_{COLLECTION_SUFFIX_PUBLICACOES}"


def collection_processos(tenant_id: str) -> str:
    return f"{_tenant_prefix(tenant_id)}_{COLLECTION_SUFFIX_PROCESSOS}"


def ensure_tenant_collections(tenant_id: str) -> None:
    """Cria as collections do tenant no Qdrant se não existirem."""
    from qdrant_client.models import Distance, VectorParams, PayloadSchemaType
    from services.embedding_service import get_client

    cfg = _get_config()
    client = get_client()
    existing = [c.name for c in client.get_collections().collections]

    for coll_name in [collection_publicacoes(tenant_id), collection_processos(tenant_id)]:
        if coll_name not in existing:
            client.create_collection(
                collection_name=coll_name,
                vectors_config=VectorParams(
                    size=cfg.embedding_dims,
                    distance=Distance.COSINE,
                ),
            )
            client.create_payload_index(coll_name, "tribunal", PayloadSchemaType.KEYWORD)
            client.create_payload_index(coll_name, "pessoa_id", PayloadSchemaType.INTEGER)
            client.create_payload_index(coll_name, "numero_processo", PayloadSchemaType.KEYWORD)
            client.create_payload_index(coll_name, "data_disponibilizacao", PayloadSchemaType.KEYWORD)
            logger.info(f"Collection '{coll_name}' criada para tenant {tenant_id}")
        else:
            logger.debug(f"Collection '{coll_name}' já existe para tenant {tenant_id}")


def delete_tenant_collections(tenant_id: str) -> None:
    """Remove as collections do tenant do Qdrant."""
    from services.embedding_service import get_client

    client = get_client()
    existing = [c.name for c in client.get_collections().collections]

    for coll_name in [collection_publicacoes(tenant_id), collection_processos(tenant_id)]:
        if coll_name in existing:
            client.delete_collection(coll_name)
            logger.warning(f"Collection '{coll_name}' removida (hard delete tenant {tenant_id})")


def migrate_global_to_tenant(tenant_id: str, batch_size: int = 100) -> dict:
    """
    Migra vetores das collections globais legacy ('publicacoes', 'processos')
    para as collections do tenant.

    Usado apenas durante a migração inicial para o tenant 'armando'.

    Returns:
        Dict com contagens: {'publicacoes': N, 'processos': N}
    """
    from services.embedding_service import get_client

    client = get_client()
    existing = [c.name for c in client.get_collections().collections]
    counts = {"publicacoes": 0, "processos": 0}

    # Garantir que collections do tenant existam
    ensure_tenant_collections(tenant_id)

    for source, suffix in [("publicacoes", "publicacoes"), ("processos", "processos")]:
        if source not in existing:
            logger.info(f"Collection global '{source}' não existe, pulando migração.")
            continue

        dest = collection_publicacoes(tenant_id) if suffix == "publicacoes" else collection_processos(tenant_id)
        offset = None
        total = 0

        while True:
            result = client.scroll(
                collection_name=source,
                limit=batch_size,
                offset=offset,
                with_vectors=True,
                with_payload=True,
            )
            points, next_offset = result

            if not points:
                break

            from qdrant_client.models import PointStruct
            client.upsert(
                collection_name=dest,
                points=[
                    PointStruct(id=p.id, vector=p.vector, payload=p.payload)
                    for p in points
                ],
            )
            total += len(points)
            logger.info(f"Migrado {total} pontos de '{source}' → '{dest}'")

            if next_offset is None:
                break
            offset = next_offset

        counts[suffix] = total

    return counts


def _get_config():
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import Config
    return Config()
