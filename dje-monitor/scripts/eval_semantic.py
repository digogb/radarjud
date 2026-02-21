#!/usr/bin/env python3
"""
Avaliação de qualidade da busca semântica.

Executa buscas e exibe os resultados com texto completo para
inspeção visual de relevância.

Uso:
    docker-compose exec api python /app/scripts/eval_semantic.py "execução fiscal"
    docker-compose exec api python /app/scripts/eval_semantic.py "execução fiscal" --tipo processos
    docker-compose exec api python /app/scripts/eval_semantic.py "execução fiscal" --tribunal TJSP --top 5
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def run(query: str, tipo: str, tribunal: str | None, top: int, threshold: float):
    from services.embedding_service import search_publicacoes, search_processos
    from storage.repository import DiarioRepository
    from config import Config

    cfg = Config()
    repo = DiarioRepository(cfg.database_url)

    print(f"\n{'='*70}")
    print(f"  QUERY    : {query!r}")
    print(f"  TIPO     : {tipo}")
    print(f"  TRIBUNAL : {tribunal or 'todos'}")
    print(f"  THRESHOLD: {threshold}  |  TOP: {top}")
    print(f"{'='*70}\n")

    if tipo == "processos":
        results = search_processos(
            query=query, tribunal=tribunal,
            limit=top, score_threshold=threshold,
        )
    else:
        results = search_publicacoes(
            query=query, tribunal=tribunal,
            limit=top, score_threshold=threshold,
        )

    if not results:
        print("  Nenhum resultado encontrado.\n")
        return

    # Enriquecer com texto completo do PostgreSQL
    if tipo == "publicacoes":
        from storage.models import PublicacaoMonitorada
        pub_ids = [r["pub_id"] for r in results]
        with repo.get_session() as session:
            pubs = session.query(PublicacaoMonitorada).filter(
                PublicacaoMonitorada.id.in_(pub_ids)
            ).all()
            pub_map = {p.id: p for p in pubs}
        for r in results:
            pub = pub_map.get(r["pub_id"])
            if pub:
                r["_texto_completo"] = pub.texto_completo or pub.texto_resumo or ""
                r["_numero_processo"] = pub.numero_processo or ""
                r["_orgao"] = pub.orgao or ""
                r["_data"] = pub.data_disponibilizacao or ""
                r["_tribunal"] = pub.tribunal or ""
    else:
        for r in results:
            r["_texto_completo"] = r.get("texto_resumo", "")
            r["_numero_processo"] = r.get("numero_processo", "")
            r["_orgao"] = ""
            r["_data"] = ""
            r["_tribunal"] = r.get("tribunal", "")

    bar_chars = 30
    for i, r in enumerate(results, 1):
        score = r["score"]
        # Barra visual de score
        filled = int(score * bar_chars)
        if score >= 0.7:
            bar_color = "\033[92m"   # verde
        elif score >= 0.5:
            bar_color = "\033[93m"   # amarelo
        else:
            bar_color = "\033[91m"   # vermelho
        reset = "\033[0m"
        bar = bar_color + "█" * filled + "░" * (bar_chars - filled) + reset

        print(f"  [{i:02d}] Score: {bar} {score:.4f}")
        print(f"       Processo : {r['_numero_processo'] or '-'}")
        print(f"       Tribunal : {r['_tribunal'] or '-'}  |  Data: {r['_data'] or '-'}")
        if r["_orgao"]:
            print(f"       Órgão    : {r['_orgao']}")

        texto = r["_texto_completo"]
        if texto:
            # Truncar e mostrar as primeiras ~300 chars
            trecho = texto.strip().replace("\n", " ")[:300]
            if len(texto) > 300:
                trecho += "..."
            print(f"       Texto    : {trecho}")
        print()

    # Resumo de scores
    scores = [r["score"] for r in results]
    print(f"{'─'*70}")
    print(f"  {len(results)} resultado(s) | "
          f"min={min(scores):.4f} max={max(scores):.4f} avg={sum(scores)/len(scores):.4f}")
    print(f"  Alta relevância (>=0.70): {sum(1 for s in scores if s >= 0.70)}")
    print(f"  Média relevância (0.5-0.7): {sum(1 for s in scores if 0.5 <= s < 0.70)}")
    print(f"  Baixa relevância (<0.50): {sum(1 for s in scores if s < 0.50)}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Avalia qualidade da busca semântica")
    parser.add_argument("query", help="Texto a buscar")
    parser.add_argument("--tipo", choices=["publicacoes", "processos"], default="publicacoes")
    parser.add_argument("--tribunal", default=None, help="Ex: TJSP")
    parser.add_argument("--top", type=int, default=10, help="Quantidade de resultados")
    parser.add_argument("--threshold", type=float, default=0.35, help="Score mínimo")
    args = parser.parse_args()

    run(
        query=args.query,
        tipo=args.tipo,
        tribunal=args.tribunal,
        top=args.top,
        threshold=args.threshold,
    )
