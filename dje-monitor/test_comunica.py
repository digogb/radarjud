#!/usr/bin/env python3
"""Script para testar o ComunicaCollector"""

import sys
from datetime import date, timedelta
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from collectors.comunica_collector import ComunicaCollector


def testar_busca_por_nome():
    """Testa busca por nome no Comunica PJe"""
    print("=== Testando ComunicaCollector ===\n")

    # Datas de teste
    data_fim = date.today()
    data_inicio = data_fim - timedelta(days=60)

    print(f"Período: {data_inicio} a {data_fim}")
    print(f"Busca: jane mary\n")

    try:
        with ComunicaCollector(headless=True) as collector:
            resultados = collector.buscar_por_nome(
                nome="jane mary",
                data_inicio=data_inicio,
                data_fim=data_fim,
            )

            print(f"\n✓ Encontrados {len(resultados)} resultados\n")

            for i, resultado in enumerate(resultados[:5], 1):
                print(f"--- Resultado {i} ---")
                print(f"Tribunal: {resultado.get('tribunal', 'N/A')}")
                print(f"Data: {resultado.get('data', 'N/A')}")
                print(f"URL: {resultado.get('url', 'N/A')}")
                print(f"Texto (primeiros 200 chars):")
                print(resultado.get('texto', '')[:200])
                print()

    except Exception as e:
        print(f"\n✗ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


def testar_busca_por_cpf():
    """Testa busca por CPF no Comunica PJe"""
    print("\n=== Testando busca por CPF ===\n")

    data_fim = date.today()
    data_inicio = data_fim - timedelta(days=30)

    cpf_teste = "19998153867"  # CPF da config

    print(f"Período: {data_inicio} a {data_fim}")
    print(f"CPF: {cpf_teste}\n")

    try:
        with ComunicaCollector(headless=True) as collector:
            resultados = collector.buscar_por_cpf(
                cpf=cpf_teste,
                data_inicio=data_inicio,
                data_fim=data_fim,
            )

            print(f"\n✓ Encontrados {len(resultados)} resultados para CPF")

            if resultados:
                print("\nPrimeiro resultado:")
                print(resultados[0].get('texto', '')[:300])

    except Exception as e:
        print(f"\n✗ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    print("Iniciando testes do ComunicaCollector...\n")
    print("IMPORTANTE: Este teste requer Chrome/Chromium instalado\n")

    sucesso = True

    # Teste 1: Busca por nome
    if not testar_busca_por_nome():
        sucesso = False

    # Teste 2: Busca por CPF
    if not testar_busca_por_cpf():
        sucesso = False

    if sucesso:
        print("\n✓ Todos os testes concluídos!")
    else:
        print("\n✗ Alguns testes falharam")
        sys.exit(1)
