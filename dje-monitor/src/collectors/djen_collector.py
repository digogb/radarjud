"""
Coletor para o DJEN - Diário de Justiça Eletrônico Nacional (CNJ).

Fonte: https://comunica.pje.jus.br/
Cobertura: Todos os tribunais que usam PJe.
"""

import logging
import re
from datetime import date
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseCollector, DiarioItem

logger = logging.getLogger(__name__)


class DJENCollector(BaseCollector):
    """
    Coletor para o DJEN (comunica.pje.jus.br).

    O DJEN disponibiliza publicações de todos os tribunais que usam PJe.
    Possui interface de busca textual que permite buscar diretamente por CPF.
    """

    BASE_URL = "https://comunica.pje.jus.br"
    API_URL = "https://comunicaapi.pje.jus.br/api/v1/comunicacao"

    # Mapeamento de siglas para IDs de órgão no DJEN
    ORGAOS = {
        "TJCE": "TJCE",
        "TJSP": "TJSP",
        "TJRJ": "TJRJ",
        "TJMG": "TJMG",
        "TJRS": "TJRS",
        "TJPR": "TJPR",
        "TJSC": "TJSC",
        "TJBA": "TJBA",
        "TJPE": "TJPE",
        "TJGO": "TJGO",
        "TRF1": "TRF1",
        "TRF2": "TRF2",
        "TRF3": "TRF3",
        "TRF4": "TRF4",
        "TRF5": "TRF5",
        "TRT1": "TRT1",
        "TST": "TST",
        "STJ": "STJ",
    }

    def __init__(self, tribunal: str = "TJCE", **kwargs):
        super().__init__(tribunal=tribunal, **kwargs)
        self.orgao_id = self.ORGAOS.get(tribunal, tribunal)

    def listar_edicoes(self, data: date) -> list[DiarioItem]:
        """
        Lista edições do DJEN para o tribunal e data especificados.

        Faz scraping da página de consulta do DJEN para encontrar
        edições disponíveis.
        """
        logger.info(f"Listando edições DJEN para {self.tribunal} em {data}")
        items = []

        url = f"{self.BASE_URL}/consulta"
        params = {
            "orgao": self.orgao_id,
            "dataInicial": data.strftime("%Y-%m-%d"),
            "dataFinal": data.strftime("%Y-%m-%d"),
        }

        response = self._fazer_requisicao("GET", url, params=params)
        if not response:
            return items

        try:
            # O DJEN pode retornar JSON ou HTML dependendo do endpoint
            content_type = response.headers.get("content-type", "")

            if "application/json" in content_type:
                items = self._parse_json_response(response.json(), data)
            else:
                items = self._parse_html_response(response.text, data)
        except Exception as e:
            logger.error(f"Erro ao parsear resposta do DJEN: {e}")

        logger.info(f"Encontradas {len(items)} edições no DJEN")
        return items

    def buscar_por_termo(
        self, termo: str, data_inicio: date, data_fim: date
    ) -> list[dict]:
        """Implementação do método abstrato - Alias para buscar_por_nome."""
        return self.buscar_por_nome(termo, data_inicio, data_fim)

    def buscar_por_termo(
        self, termo: str, data_inicio: date, data_fim: date
    ) -> list[dict]:
        """Implementação do método abstrato - Alias para buscar_por_nome."""
        return self.buscar_por_nome(termo, data_inicio, data_fim)

    def buscar_por_nome(
        self, nome: str, data_inicio: date, data_fim: date, max_paginas: int = 50
    ) -> list[dict]:
        """
        Busca comunicações no DJEN pelo Nome da Parte.
        Retorna lista de resultados estruturados.
        """
        logger.info(
            f"Buscando '{nome}' no DJEN ({data_inicio} a {data_fim}) - Máx {max_paginas} págs"
        )
        resultados = []

        params = {
            "nomeParte": nome,
            "itensPorPagina": 100,
            "pagina": 1,
        }

        # Loop de paginação
        while True:
            logger.info(f"Buscando página {params['pagina']}...")
            try:
                response = self._fazer_requisicao(
                    "GET", self.API_URL, params=params, headers={"Accept": "application/json"}
                )
                
                if response and response.status_code == 200:
                    # Debug: verificar content type
                    ct = response.headers.get("content-type", "")
                    if "html" in ct:
                         raise ValueError("API retornou HTML")

                    data_resp = response.json()
                    
                    novos_items = []
                    if "items" in data_resp:
                        novos_items = self._parse_comunicacoes_json(data_resp["items"], nome)
                    elif isinstance(data_resp, list):
                         novos_items = self._parse_comunicacoes_json(data_resp, nome)
                    
                    if not novos_items:
                        break
                        
                    resultados.extend(novos_items)
                    
                    # Verificar se há mais páginas (baseado no total ou apenas se trouxe items)
                    total_count = data_resp.get("count", 0) if isinstance(data_resp, dict) else len(novos_items)
                    # Se trouxe menos que o limite, provavelmente acabou
                    if len(novos_items) < params["itensPorPagina"]:
                        break
                        
                    params["pagina"] += 1
                    
                    # Limite de segurança para não loopar infinito
                    if params["pagina"] > max_paginas:
                        logger.warning(f"Limite de {max_paginas} páginas atingido na busca por nome.")
                        break
                else:
                    logger.warning(f"Erro na requisição (Pag {params['pagina']}): Status {response.status_code if response else 'None'}")
                    break
                    
            except Exception as e:
                logger.warning(f"Erro na API direta ({self.API_URL}): {e}")
                break
        
        return resultados

        return resultados


    def _parse_comunicacoes_json(self, items: list, termo: str) -> list[dict]:
        """Parseia comunicações retornadas pela API JSON."""
        resultados = []
        for item in items:
            try:
                # Extrair dados ricos do JSON
                res = {
                    "tribunal": item.get("siglaTribunal", self.tribunal),
                    "processo": item.get("numeroProcesso", ""),
                    "data_disponibilizacao": item.get("dataDisponibilizacao", ""),
                    "orgao": item.get("nomeOrgao", ""),
                    "tipo_comunicacao": item.get("tipoComunicacao", ""),
                    "texto": item.get("texto", item.get("conteudo", "")),
                    "meio": item.get("meio", ""),
                    "link": item.get("link", ""),
                    "id": item.get("id", ""),
                    "termo_buscado": termo,
                    "fonte": "DJEN API",
                    # Dados extras para contexto
                    "partes": [p.get("nome", "") for p in item.get("destinatarios", [])],
                    "raw_data": item # Guarda dados brutos para debug
                }
                
                # Se não tiver texto no item principal, tentar montar do HTML ou buscar link
                if not res["texto"] and res["id"]:
                     res["texto"] = f"Comunicação ID {res['id']} - Ver link: {res['link']}"

                resultados.append(res)
            except Exception as e:
                logger.error(f"Erro ao parsear item JSON: {e}")
                
        return resultados

    def obter_url_pdf_diario(self, diario_id: str) -> Optional[str]:
        """Obtém URL de download do PDF de um diário específico."""
        url = f"{self.BASE_URL}/diario/{diario_id}/download"
        response = self._fazer_requisicao("HEAD", url)
        if response and response.status_code == 200:
            return url
        return None

    def _parse_json_response(self, data: dict, dt: date) -> list[DiarioItem]:
        """Parseia resposta JSON do DJEN."""
        items = []

        # Estrutura pode variar - tentamos formatos conhecidos
        diarios = data if isinstance(data, list) else data.get("diarios", [])

        for diario in diarios:
            try:
                item = DiarioItem(
                    tribunal=self.tribunal,
                    data_publicacao=dt,
                    caderno=str(diario.get("caderno", "")),
                    caderno_nome=diario.get("descricaoCaderno", ""),
                    url_pdf=urljoin(
                        self.BASE_URL,
                        diario.get("linkDownload", diario.get("url", "")),
                    ),
                    edicao=str(diario.get("numero", diario.get("edicao", ""))),
                    num_paginas=diario.get("quantidadePaginas", 0),
                    metadata={"fonte": "DJEN", "diario_id": diario.get("id")},
                )
                items.append(item)
            except Exception as e:
                logger.warning(f"Erro ao parsear diário DJEN: {e}")

        return items

    def _parse_html_response(self, html: str, dt: date) -> list[DiarioItem]:
        """Parseia resposta HTML do DJEN."""
        items = []
        soup = BeautifulSoup(html, "html.parser")

        # Busca links de download de diários
        # Padrões comuns no DJEN:
        # - Links com classe específica
        # - Tabelas com listagem de edições
        for link in soup.select("a[href*='download'], a[href*='diario']"):
            href = link.get("href", "")
            if not href:
                continue

            texto = link.get_text(strip=True)
            url_pdf = urljoin(self.BASE_URL, href)

            # Tentar extrair número do caderno do texto ou atributos
            caderno = self._extrair_caderno(link, texto)
            edicao = self._extrair_edicao(link, texto)

            item = DiarioItem(
                tribunal=self.tribunal,
                data_publicacao=dt,
                caderno=caderno,
                caderno_nome=texto,
                url_pdf=url_pdf,
                edicao=edicao,
                metadata={"fonte": "DJEN"},
            )
            items.append(item)

        return items

    def _parse_busca_json(self, data: dict, termo: str) -> list[dict]:
        """Parseia resultados de busca JSON."""
        resultados = []
        items = data if isinstance(data, list) else data.get("resultados", [])

        for item in items:
            resultados.append(
                {
                    "tribunal": self.tribunal,
                    "data": item.get("dataPublicacao", ""),
                    "caderno": item.get("caderno", ""),
                    "texto": item.get("conteudo", item.get("texto", "")),
                    "url": urljoin(self.BASE_URL, item.get("link", "")),
                    "termo_buscado": termo,
                    "fonte": "DJEN",
                }
            )

        return resultados

    def _parse_busca_html(self, html: str, termo: str) -> list[dict]:
        """Parseia resultados de busca HTML."""
        resultados = []
        soup = BeautifulSoup(html, "html.parser")

        # Busca por elementos que contenham resultados
        # Busca por elementos que contenham resultados (cards de comunicação)
        # Adaptado para o layout da imagem (cards com azul no topo)
        for card in soup.select("div.card, div.resultado, app-comunicacao-card"):
            texto_full = card.get_text(" ", strip=True)
            
            # Tentar extrair número do processo (padrão NNNNNNN-DD.AAAA.J.TR.OOOO)
            proc_match = re.search(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}", texto_full)
            processo = proc_match.group(0) if proc_match else ""

            # Extrair data (DD/MM/AAAA)
            data_match = re.search(r"\d{2}/\d{2}/\d{4}", texto_full)
            data_disp = data_match.group(0) if data_match else ""
            
            # Extrair órgão (geralmente logo no início ou após rótulo)
            orgao = ""
            if "Órgão:" in texto_full:
                parts = texto_full.split("Órgão:")
                if len(parts) > 1:
                    orgao = parts[1].split("\n")[0].split("Data")[0].strip()

            resultados.append(
                {
                    "tribunal": self.tribunal,
                    "processo": processo,
                    "data_disponibilizacao": data_disp,
                    "orgao": orgao,
                    "texto": texto_full[:3000], # Limitar tamanho
                    "termo_buscado": termo,
                    "fonte": "DJEN HTML",
                }
            )

        return resultados

    def _extrair_caderno(self, element, texto: str) -> str:
        """Tenta extrair identificador do caderno."""
        # Busca em atributos data-*
        for attr in element.attrs:
            if "caderno" in attr.lower():
                return str(element[attr])

        # Busca no texto
        match = re.search(r"caderno\s*(\d+)", texto, re.IGNORECASE)
        if match:
            return match.group(1)

        return "0"

    def _extrair_edicao(self, element, texto: str) -> str:
        """Tenta extrair número da edição."""
        for attr in element.attrs:
            if "edicao" in attr.lower() or "numero" in attr.lower():
                return str(element[attr])

        match = re.search(r"(?:edi[çc][aã]o|n[úu]mero)\s*(\d+)", texto, re.IGNORECASE)
        if match:
            return match.group(1)

        return ""
