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
        """
        Busca publicações no DJEN contendo o termo (ex: CPF).

        O DJEN permite busca textual, o que é mais eficiente
        do que baixar todos os PDFs.
        """
        logger.info(
            f"Buscando '{termo}' no DJEN ({data_inicio} a {data_fim})"
        )
        resultados = []

        url = f"{self.BASE_URL}/consulta"
        params = {
            "orgao": self.orgao_id,
            "dataInicial": data_inicio.strftime("%Y-%m-%d"),
            "dataFinal": data_fim.strftime("%Y-%m-%d"),
            "texto": termo,
        }

        response = self._fazer_requisicao("GET", url, params=params)
        if not response:
            return resultados

        try:
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                data_resp = response.json()
                resultados = self._parse_busca_json(data_resp, termo)
            else:
                resultados = self._parse_busca_html(response.text, termo)
        except Exception as e:
            logger.error(f"Erro ao parsear busca DJEN: {e}")

        logger.info(f"Encontrados {len(resultados)} resultados para '{termo}'")
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
        for resultado in soup.select(
            ".resultado, .item-resultado, tr, .card, .list-group-item"
        ):
            texto = resultado.get_text(strip=True)
            if termo.replace(".", "").replace("-", "") in texto.replace(
                ".", ""
            ).replace("-", ""):
                link = resultado.find("a")
                url = ""
                if link:
                    url = urljoin(self.BASE_URL, link.get("href", ""))

                resultados.append(
                    {
                        "tribunal": self.tribunal,
                        "texto": texto[:2000],
                        "url": url,
                        "termo_buscado": termo,
                        "fonte": "DJEN",
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
