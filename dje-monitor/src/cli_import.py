"""
CLI para importação de pessoas monitoradas a partir de planilha Excel.

Uso:
    python src/cli_import.py pessoas.xlsx
    python src/cli_import.py pessoas.xlsx --dry-run
    python src/cli_import.py pessoas.xlsx --desativar-expirados
"""

import argparse
import logging
import os
import sys

# Adiciona src ao path para imports funcionarem
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from storage.repository import DiarioRepository
from services.import_pessoas import importar_planilha


def main():
    parser = argparse.ArgumentParser(
        description="Importa partes adversas de planilha Excel como pessoas monitoradas no DJe Monitor."
    )
    parser.add_argument("arquivo", help="Caminho para o arquivo pessoas.xlsx")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas valida e exibe o que seria importado, sem gravar no banco",
    )
    parser.add_argument(
        "--desativar-expirados",
        action="store_true",
        help="Após importar, desativa pessoas cujo prazo de monitoramento já expirou",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Exibe logs detalhados de cada linha processada",
    )
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    config = Config()
    repo = DiarioRepository(config.database_url)

    if args.dry_run:
        print(f"\n[DRY RUN] Simulando importação de: {args.arquivo}\n")
    else:
        print(f"\nImportando: {args.arquivo}\n")

    try:
        stats = importar_planilha(args.arquivo, repo, dry_run=args.dry_run)
    except FileNotFoundError as e:
        print(f"ERRO: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"ERRO na planilha: {e}")
        sys.exit(1)

    print("\n=== Resultado da Importação ===")
    print(f"  Total de linhas:   {stats['total']}")
    print(f"  Importados:        {stats['importados']}")
    print(f"  Pulados (vazios):  {stats['pulados']}")
    print(f"  Erros:             {stats['erros']}")

    if args.desativar_expirados and not args.dry_run:
        count = repo.desativar_expirados()
        print(f"  Expirados desativados: {count}")

    if args.dry_run:
        print("\n[DRY RUN] Nenhum dado foi gravado no banco.")

    print()


if __name__ == "__main__":
    main()
