"""
Coletor para o DJEN - Diário de Justiça Eletrônico Nacional (CNJ).

Fonte: https://comunica.pje.jus.br/
Cobertura: Todos os tribunais que usam PJe.

Este módulo é um wrapper fino sobre o pacote ``dje-search-client``, que contém
a lógica de busca reutilizável. Qualquer produto que precise consultar o DJEN
deve usar DJESearchClient diretamente, sem depender deste collector.
"""

import logging
import re
from datetime import date
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from dje_search import DJESearchClient, DJESearchParams
from .base import BaseCollector, DiarioItem

logger = logging.getLogger(__name__)


class DJENCollector(BaseCollector):
    """
    Coletor para o DJEN (comunica.pje.jus.br).

    Implementa a interface BaseCollector do radarjud delegando a busca real
    ao DJESearchClient do pacote dje-search-client.
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
        self._search_client = DJESearchClient(
            timeout=kwargs.get("timeout", 60),
            delay=kwargs.get("delay", 1.5),
            max_retries=kwargs.get("max_retries", 3),
        )

    # ------------------------------------------------------------------
    # Métodos da interface BaseCollector
    # ------------------------------------------------------------------

    def buscar_por_termo(
        self, termo: str, data_inicio: date = None, data_fim: date = None
    ) -> list[dict]:
        """Implementação do método abstrato — delega para buscar_por_nome."""
        return self.buscar_por_nome(termo, data_inicio=data_inicio, data_fim=data_fim)

    def buscar_por_nome(
        self,
        nome: str,
        data_inicio: date = None,
        data_fim: date = None,
        max_paginas: int = 50,
    ) -> list[dict]:
        """
        Busca comunicações no DJEN pelo Nome da Parte ou Número do Processo.

        Auto-detecta se ``nome`` é um número de processo (≥15 dígitos ou
        contém "-" no formato CNJ) e usa o parâmetro correto da API.

        Retorna lista de dicts no formato legado do radarjud.
        """
        logger.info("Buscando '%s' no DJEN — máx %d páginas", nome, max_paginas)

        termo_limpo = re.sub(r"\D", "", nome)
        is_processo = len(termo_limpo) >= 15 and ("-" in nome or len(termo_limpo) == 20)

        if is_processo:
            logger.info("Detectado busca por processo: %s", nome)
            params = DJESearchParams(
                numero_processo=nome,
                data_inicio=data_inicio,
                data_fim=data_fim,
                max_paginas=max_paginas,
            )
        else:
            params = DJESearchParams(
                nome_parte=nome,
                data_inicio=data_inicio,
                data_fim=data_fim,
                max_paginas=max_paginas,
            )

        comunicacoes = self._search_client.buscar(params)
        return [c.to_dict() for c in comunicacoes]

    def buscar_avancado(self, params: DJESearchParams) -> list[dict]:
        """
        Busca com parâmetros completos — expõe toda a capacidade do DJESearchClient.

        Use este método quando precisar buscar por advogado, OAB, CPF/CNPJ
        ou combinar múltiplos filtros.

        Exemplo::

            resultados = collector.buscar_avancado(DJESearchParams(
                nome_advogado="JOSE DA SILVA",
                sigla_tribunal="TJCE",
                data_inicio=date(2025, 1, 1),
            ))
        """
        comunicacoes = self._search_client.buscar(params)
        return [c.to_dict() for c in comunicacoes]

    # ------------------------------------------------------------------
    # Listagem de edições (scraping HTML — não alterado)
    # ------------------------------------------------------------------

    def listar_edicoes(self, data: date) -> list[DiarioItem]:
        """
        Lista edições do DJEN para o tribunal e data especificados.

        Faz scraping da página de consulta do DJEN para encontrar
        edições disponíveis.
        """
        logger.info("Listando edições DJEN para %s em %s", self.tribunal, data)
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
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                items = self._parse_json_response(response.json(), data)
            else:
                items = self._parse_html_response(response.text, data)
        except Exception as exc:
            logger.error("Erro ao parsear resposta do DJEN: %s", exc)

        logger.info("Encontradas %d edições no DJEN", len(items))
        return items

    def obter_url_pdf_diario(self, diario_id: str) -> Optional[str]:
        """Obtém URL de download do PDF de um diário específico."""
        url = f"{self.BASE_URL}/diario/{diario_id}/download"
        response = self._fazer_requisicao("HEAD", url)
        if response and response.status_code == 200:
            return url
        return None

    # ------------------------------------------------------------------
    # Parsing de edições (legado — scraping HTML/JSON)
    # ------------------------------------------------------------------

    def _parse_json_response(self, data: dict, dt: date) -> list[DiarioItem]:
        items = []
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
            except Exception as exc:
                logger.warning("Erro ao parsear diário DJEN: %s", exc)
        return items

    def _parse_html_response(self, html: str, dt: date) -> list[DiarioItem]:
        items = []
        soup = BeautifulSoup(html, "html.parser")
        for link in soup.select("a[href*='download'], a[href*='diario']"):
            href = link.get("href", "")
            if not href:
                continue
            texto = link.get_text(strip=True)
            url_pdf = urljoin(self.BASE_URL, href)
            caderno = self._extrair_caderno(link, texto)
            edicao = self._extrair_edicao(link, texto)
            items.append(DiarioItem(
                tribunal=self.tribunal,
                data_publicacao=dt,
                caderno=caderno,
                caderno_nome=texto,
                url_pdf=url_pdf,
                edicao=edicao,
                metadata={"fonte": "DJEN"},
            ))
        return items

    def _extrair_caderno(self, element, texto: str) -> str:
        for attr in element.attrs:
            if "caderno" in attr.lower():
                return str(element[attr])
        match = re.search(r"caderno\s*(\d+)", texto, re.IGNORECASE)
        return match.group(1) if match else "0"

    def _extrair_edicao(self, element, texto: str) -> str:
        for attr in element.attrs:
            if "edicao" in attr.lower() or "numero" in attr.lower():
                return str(element[attr])
        match = re.search(r"(?:edi[çc][aã]o|n[úu]mero)\s*(\d+)", texto, re.IGNORECASE)
        return match.group(1) if match else ""
