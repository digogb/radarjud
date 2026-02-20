"""
Script para indexar publicações existentes no Qdrant (backfill).

Uso:
    python scripts/backfill_embeddings.py
    python scripts/backfill_embeddings.py --batch-size 200 --collection publicacoes
    python scripts/backfill_embeddings.py --collection processos
"""
import argparse
import os
import sys

# Adiciona src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config import Config
from storage.repository import DiarioRepository
from services.embedding_service import (
    ensure_collections,
    index_publicacao,
    index_processo,
)


def backfill_publicacoes(repo: DiarioRepository, batch_size: int = 100):
    ensure_collections()
    offset = 0
    total = 0

    while True:
        pubs = repo.get_publicacoes_batch(offset=offset, limit=batch_size)
        if not pubs:
            break
        for pub in pubs:
            try:
                index_publicacao(pub.id, pub.to_dict())
                total += 1
            except Exception as e:
                print(f"  ERRO pub {pub.id}: {e}")
        offset += batch_size
        print(f"  → {total} publicações indexadas...")

    print(f"Backfill publicações completo: {total}")


def backfill_processos(repo: DiarioRepository):
    ensure_collections()
    processos = repo.get_all_processos_com_publicacoes()
    total = 0

    for proc in processos:
        try:
            index_processo(proc["numero_processo"], proc)
            total += 1
        except Exception as e:
            print(f"  ERRO processo {proc.get('numero_processo')}: {e}")

    print(f"Backfill processos completo: {total}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill de embeddings semânticos no Qdrant")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument(
        "--collection",
        choices=["publicacoes", "processos", "all"],
        default="all",
    )
    args = parser.parse_args()

    cfg = Config()
    repo = DiarioRepository(cfg.database_url)

    if args.collection in ("publicacoes", "all"):
        print(f"Iniciando backfill de publicações (batch={args.batch_size})...")
        backfill_publicacoes(repo, args.batch_size)

    if args.collection in ("processos", "all"):
        print("Iniciando backfill de processos...")
        backfill_processos(repo)
