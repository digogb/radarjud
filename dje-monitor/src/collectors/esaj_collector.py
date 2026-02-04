"""
Coletor para DJe via sistema e-SAJ.

Funciona para tribunais que usam o sistema e-SAJ do TJSP:
- TJCE (SAJ): https://esaj.tjce.jus.br/cdje/
- TJSP: https://dje.tjsp.jus.br/
- Outros TJs que utilizam e-SAJ.
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


class ESAJCollector(BaseCollector):
    """
    Coletor para DJe via sistema e-SAJ.

    O e-SAJ é o sistema de automação judiciária do TJSP, utilizado
    por diversos tribunais estaduais.
    """

    TRIBUNAIS = {
        "TJCE": {
            "base_url": "https://esaj.tjce.jus.br",
            "path_cdje": "/cdje",
        },
        "TJSP": {
            "base_url": "https://dje.tjsp.jus.br",
            "path_cdje": "",
        },
    }

    CADERNOS = {
        1: "Administrativo",
        2: "Judicial - 2ª Instância",
        3: "Judicial - 1ª Instância Capital",
        10: "Judicial - 1ª Instância Interior",
        11: "Editais e Leilões",
    }

    def __init__(self, tribunal: str = "TJCE", **kwargs):
        super().__init__(tribunal=tribunal, **kwargs)

        config = self.TRIBUNAIS.get(tribunal)
        if not config:
            raise ValueError(
                f"Tribunal '{tribunal}' não suportado pelo e-SAJ. "
                f"Disponíveis: {list(self.TRIBUNAIS.keys())}"
            )

        self.base_url = config["base_url"]
        self.path_cdje = config["path_cdje"]

    def listar_edicoes(self, data: date) -> list[DiarioItem]:
        """
        Lista cadernos disponíveis para uma data.

        Acessa a página de consulta do e-SAJ e identifica
        os cadernos publicados na data especificada.
        """
        logger.info(f"Listando edições e-SAJ para {self.tribunal} em {data}")
        items = []

        # Primeiro, descobrir o número do diário para a data
        diario_info = self._obter_info_diario(data)
        if not diario_info:
            logger.info(f"Nenhum diário encontrado para {data}")
            return items

        nu_diario = diario_info.get("nuDiario", "")
        cd_volume = diario_info.get("cdVolume", "")

        # Listar cadernos disponíveis
        for cd_caderno, nome_caderno in self.CADERNOS.items():
            url_pdf = self._construir_url_caderno(
                nu_diario, cd_volume, cd_caderno
            )
            if url_pdf:
                item = DiarioItem(
                    tribunal=self.tribunal,
                    data_publicacao=data,
                    caderno=str(cd_caderno),
                    caderno_nome=nome_caderno,
                    url_pdf=url_pdf,
                    edicao=nu_diario,
                    metadata={
                        "fonte": "e-SAJ",
                        "nuDiario": nu_diario,
                        "cdVolume": cd_volume,
                        "cdCaderno": cd_caderno,
                    },
                )
                items.append(item)

        logger.info(f"Encontrados {len(items)} cadernos no e-SAJ")
        return items

    def buscar_por_termo(
        self, termo: str, data_inicio: date, data_fim: date
    ) -> list[dict]:
        """
        Busca publicações no e-SAJ contendo o termo.

        Utiliza a consulta avançada do e-SAJ que permite
        busca por palavra-chave.
        """
        logger.info(
            f"Buscando '{termo}' no e-SAJ ({data_inicio} a {data_fim})"
        )
        resultados = []

        url = f"{self.base_url}{self.path_cdje}/consultaAvancada.do"

        data_form = {
            "dadosConsulta.pesquisaLivre": termo,
            "dadosConsulta.dtInicio": data_inicio.strftime("%d/%m/%Y"),
            "dadosConsulta.dtFim": data_fim.strftime("%d/%m/%Y"),
            "dadosConsulta.cdCaderno": "",  # Todos os cadernos
        }

        response = self._fazer_requisicao("POST", url, data=data_form)
        if not response:
            return resultados

        resultados = self._parse_resultados_busca(response.text, termo)

        # Verificar paginação
        pagina = 2
        while True:
            proxima = self._obter_proxima_pagina(response.text, pagina)
            if not proxima:
                break

            response = self._fazer_requisicao("GET", proxima)
            if not response:
                break

            novos = self._parse_resultados_busca(response.text, termo)
            if not novos:
                break

            resultados.extend(novos)
            pagina += 1

        logger.info(f"Encontrados {len(resultados)} resultados no e-SAJ")
        return resultados

    def buscar_por_caderno(
        self, data: date, cd_caderno: int
    ) -> Optional[DiarioItem]:
        """Busca um caderno específico para uma data."""
        diario_info = self._obter_info_diario(data)
        if not diario_info:
            return None

        nu_diario = diario_info.get("nuDiario", "")
        cd_volume = diario_info.get("cdVolume", "")

        url_pdf = self._construir_url_caderno(nu_diario, cd_volume, cd_caderno)
        if not url_pdf:
            return None

        return DiarioItem(
            tribunal=self.tribunal,
            data_publicacao=data,
            caderno=str(cd_caderno),
            caderno_nome=self.CADERNOS.get(cd_caderno, f"Caderno {cd_caderno}"),
            url_pdf=url_pdf,
            edicao=nu_diario,
            metadata={
                "fonte": "e-SAJ",
                "nuDiario": nu_diario,
                "cdVolume": cd_volume,
                "cdCaderno": cd_caderno,
            },
        )

    def _obter_info_diario(self, data: date) -> Optional[dict]:
        """
        Obtém informações do diário para uma data.

        Faz consulta ao e-SAJ para descobrir o número do diário
        e volume para a data especificada.
        """
        url = f"{self.base_url}{self.path_cdje}/consultaSimples.do"
        params = {
            "dtDiario": data.strftime("%d/%m/%Y"),
        }

        response = self._fazer_requisicao("GET", url, params=params)
        if not response:
            return None

        return self._extrair_info_diario(response.text, data)

    def _extrair_info_diario(self, html: str, data: date) -> Optional[dict]:
        """Extrai informações do diário do HTML da resposta."""
        soup = BeautifulSoup(html, "html.parser")

        info = {
            "nuDiario": "",
            "cdVolume": "",
            "data": data,
        }

        # Buscar em campos hidden ou no conteúdo
        for inp in soup.select("input[type='hidden']"):
            name = inp.get("name", "")
            value = inp.get("value", "")

            if "nuDiario" in name:
                info["nuDiario"] = value
            elif "cdVolume" in name:
                info["cdVolume"] = value

        # Fallback: buscar no texto da página
        if not info["nuDiario"]:
            match = re.search(
                r"(?:di[áa]rio|edi[çc][aã]o)\s*(?:n[ºo°.]?\s*)?(\d+)",
                soup.get_text(),
                re.IGNORECASE,
            )
            if match:
                info["nuDiario"] = match.group(1)

        # Buscar em selects/options
        for option in soup.select("select option[selected], select option[value]"):
            parent_name = option.parent.get("name", "") if option.parent else ""
            if "caderno" not in parent_name.lower():
                value = option.get("value", "")
                if value and "volume" in parent_name.lower():
                    info["cdVolume"] = value

        if info["nuDiario"]:
            return info

        # Verificar se há mensagem de que não há diário para a data
        texto_pagina = soup.get_text().lower()
        if "não há" in texto_pagina or "nenhum" in texto_pagina:
            logger.debug(f"Nenhum diário encontrado para {data}")
            return None

        logger.warning(f"Não foi possível extrair info do diário para {data}")
        return None

    def _construir_url_caderno(
        self, nu_diario: str, cd_volume: str, cd_caderno: int
    ) -> Optional[str]:
        """Constrói URL para download de um caderno específico."""
        if not nu_diario:
            return None

        # URL padrão do e-SAJ para download de caderno
        url = (
            f"{self.base_url}{self.path_cdje}/downloadCaderno.do?"
            f"nuDiario={nu_diario}&cdVolume={cd_volume}"
            f"&cdCaderno={cd_caderno}"
        )

        # Verificar se o caderno existe com HEAD request
        try:
            response = self.client.head(url, follow_redirects=True)
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                if "pdf" in content_type.lower() or "octet-stream" in content_type.lower():
                    return url
        except Exception:
            pass

        # URL alternativa - consulta por página
        url_alt = (
            f"{self.base_url}{self.path_cdje}/consultaSimples.do?"
            f"cdVolume={cd_volume}&nuDiario={nu_diario}"
            f"&cdCaderno={cd_caderno}&nuSeqpagina=1"
        )

        return url_alt

    def _parse_resultados_busca(self, html: str, termo: str) -> list[dict]:
        """Parseia resultados da busca avançada do e-SAJ."""
        resultados = []
        soup = BeautifulSoup(html, "html.parser")

        # Busca por elementos de resultado - vários seletores possíveis
        seletores = [
            ".resultadoPesquisa",
            ".resultado",
            "table.resultTable tr",
            ".listaResultado li",
            ".conteudoPublicacao",
        ]

        for seletor in seletores:
            elementos = soup.select(seletor)
            if elementos:
                for elem in elementos:
                    resultado = self._extrair_resultado(elem, termo)
                    if resultado:
                        resultados.append(resultado)
                break

        return resultados

    def _extrair_resultado(self, elemento, termo: str) -> Optional[dict]:
        """Extrai dados de um elemento de resultado."""
        texto = elemento.get_text(strip=True)
        if not texto or len(texto) < 10:
            return None

        # Buscar link associado
        link = elemento.find("a")
        url = ""
        if link:
            url = urljoin(self.base_url, link.get("href", ""))

        # Buscar data no texto
        data_match = re.search(r"(\d{2}/\d{2}/\d{4})", texto)
        data_pub = data_match.group(1) if data_match else ""

        # Buscar caderno
        caderno_match = re.search(r"caderno\s*(\d+)", texto, re.IGNORECASE)
        caderno = caderno_match.group(1) if caderno_match else ""

        return {
            "tribunal": self.tribunal,
            "data": data_pub,
            "caderno": caderno,
            "texto": texto[:2000],
            "url": url,
            "termo_buscado": termo,
            "fonte": "e-SAJ",
        }

    def _obter_proxima_pagina(self, html: str, pagina: int) -> Optional[str]:
        """Verifica se há próxima página de resultados."""
        soup = BeautifulSoup(html, "html.parser")

        # Buscar link de próxima página
        for link in soup.select("a.paginacao, a.proxima, a[title*='xima']"):
            href = link.get("href", "")
            if href:
                return urljoin(self.base_url, href)

        # Buscar por número de página específico
        for link in soup.select("a"):
            texto = link.get_text(strip=True)
            if texto == str(pagina):
                href = link.get("href", "")
                if href:
                    return urljoin(self.base_url, href)

        return None
