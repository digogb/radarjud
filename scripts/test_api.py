#!/usr/bin/env python3
"""Script para testar APIs de DJe"""

import httpx
from datetime import date, timedelta

def testar_djen():
    """Testa API do DJEN"""
    client = httpx.Client(timeout=30, follow_redirects=True)

    # Testar várias datas
    hoje = date.today()
    datas = [
        hoje - timedelta(days=i) for i in range(0, 30, 7)
    ]

    print("=== Testando DJEN (comunica.pje.jus.br) ===\n")

    for dt in datas:
        url = f"https://comunica.pje.jus.br/consulta"
        params = {
            "orgao": "TJCE",
            "dataInicial": dt.strftime("%Y-%m-%d"),
            "dataFinal": dt.strftime("%Y-%m-%d"),
        }

        try:
            response = client.get(url, params=params)
            content_type = response.headers.get("content-type", "")
            print(f"Data: {dt} | Status: {response.status_code} | Type: {content_type}")
            print(f"  Tamanho: {len(response.content)} bytes")

            # Se for HTML, verificar se é a aplicação ou dados
            if "text/html" in content_type:
                if "<app-root>" in response.text:
                    print("  -> Aplicação Angular (precisa de JS)")
                else:
                    print(f"  -> HTML (primeiros 200 chars): {response.text[:200]}")
            elif "application/json" in content_type:
                print(f"  -> JSON: {response.json()}")

            print()
        except Exception as e:
            print(f"Data: {dt} | Erro: {e}\n")

def testar_esaj():
    """Testa e-SAJ TJCE"""
    client = httpx.Client(timeout=30, follow_redirects=True, verify=False)

    hoje = date.today()
    datas = [
        hoje - timedelta(days=i) for i in range(0, 30, 7)
    ]

    print("\n=== Testando e-SAJ (esaj.tjce.jus.br) ===\n")

    for dt in datas:
        url = "https://esaj.tjce.jus.br/cdje/consultaSimples.do"
        params = {"dtDiario": dt.strftime("%d/%m/%Y")}

        try:
            response = client.get(url, params=params)
            print(f"Data: {dt} | Status: {response.status_code}")

            # Buscar indicadores de frameset
            if "frameset" in response.text.lower():
                # Extrair src do frame
                import re
                match = re.search(r'src="([^"]+)"', response.text)
                if match:
                    frame_src = match.group(1)
                    # Extrair nuDiario e cdVolume
                    nu_match = re.search(r'nuDiario=([^&"]+)', frame_src)
                    cd_match = re.search(r'cdVolume=([^&"]+)', frame_src)

                    if nu_match and nu_match.group(1):
                        print(f"  -> nuDiario: {nu_match.group(1)}")
                        if cd_match:
                            print(f"  -> cdVolume: {cd_match.group(1)}")
                        print("  ✓ Diário ENCONTRADO!")
                    else:
                        print("  -> Sem diário (nuDiario vazio)")

            print()
        except Exception as e:
            print(f"Data: {dt} | Erro: {e}\n")

if __name__ == "__main__":
    testar_djen()
    testar_esaj()
