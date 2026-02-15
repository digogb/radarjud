"""
Classe base para coletores de Diário da Justiça Eletrônico.
"""

import hashlib
import logging
import ssl
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


def create_legacy_ssl_context():
    """Cria contexto SSL compatível com servidores governamentais legados."""
    ctx = ssl.create_default_context()
    try:
        # Tenta permitir cifras antigas e baixar nível de segurança
        # AES256-SHA é necessário para TJCE (identificado via teste)
        ctx.set_ciphers("DEFAULT:AES256-SHA:AES128-SHA:@SECLEVEL=1")
        
        # Permitir conexão com servidores legados (OpenSSL 3.0+)
        if hasattr(ssl, "OP_LEGACY_SERVER_CONNECT"):
            ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
    except Exception as e:
        logger.warning(f"Aviso ao configurar SSL legado: {e}")

    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


@dataclass
class DiarioItem:
    """Representa uma edição/caderno do diário."""

    tribunal: str
    data_publicacao: date
    caderno: str
    caderno_nome: str
    url_pdf: str
    edicao: str = ""
    num_paginas: int = 0
    metadata: dict = field(default_factory=dict)


class BaseCollector(ABC):
    """Classe base para coletores de DJe."""

    def __init__(
        self,
        tribunal: str,
        timeout: int = 60,
        delay: float = 1.5,
        max_retries: int = 3,
    ):
        self.tribunal = tribunal
        self.delay = delay
        self.max_retries = max_retries

        self.client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            verify=create_legacy_ssl_context(),
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            },
        )

    def __del__(self):
        try:
            self.client.close()
        except Exception:
            pass

    @abstractmethod
    def listar_edicoes(self, data: date) -> list[DiarioItem]:
        """Lista edições/cadernos disponíveis para uma data."""
        ...

    @abstractmethod
    def buscar_por_termo(
        self, termo: str, data_inicio: date, data_fim: date
    ) -> list[dict]:
        """Busca publicações contendo um termo específico."""
        ...

    def baixar_pdf(self, url: str, destino: Path) -> Optional[Path]:
        """Baixa PDF da publicação com retries."""
        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)

        for tentativa in range(self.max_retries):
            try:
                self._aguardar_delay()
                logger.info(f"Baixando PDF: {url} -> {destino}")

                with self.client.stream("GET", url) as response:
                    response.raise_for_status()
                    with open(destino, "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)

                logger.info(f"PDF baixado: {destino} ({destino.stat().st_size} bytes)")
                return destino

            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"HTTP {e.response.status_code} ao baixar {url} "
                    f"(tentativa {tentativa + 1}/{self.max_retries})"
                )
            except httpx.RequestError as e:
                logger.warning(
                    f"Erro de rede ao baixar {url}: {e} "
                    f"(tentativa {tentativa + 1}/{self.max_retries})"
                )

            if tentativa < self.max_retries - 1:
                wait = 2 ** (tentativa + 1)
                logger.info(f"Aguardando {wait}s antes de nova tentativa...")
                time.sleep(wait)

        logger.error(f"Falha ao baixar PDF após {self.max_retries} tentativas: {url}")
        return None

    def calcular_hash(self, filepath: Path) -> str:
        """Calcula SHA256 de um arquivo."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _aguardar_delay(self):
        """Aguarda delay entre requisições (rate limiting)."""
        if self.delay > 0:
            time.sleep(self.delay)

    def _fazer_requisicao(
        self, method: str, url: str, **kwargs
    ) -> Optional[httpx.Response]:
        """Faz requisição HTTP com retries e backoff."""
        for tentativa in range(self.max_retries):
            try:
                self._aguardar_delay()
                response = self.client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"HTTP {e.response.status_code} em {url} "
                    f"(tentativa {tentativa + 1}/{self.max_retries})"
                )
            except httpx.RequestError as e:
                logger.warning(
                    f"Erro de rede em {url}: {e} "
                    f"(tentativa {tentativa + 1}/{self.max_retries})"
                )

            if tentativa < self.max_retries - 1:
                wait = 2 ** (tentativa + 1)
                time.sleep(wait)

        logger.error(f"Falha após {self.max_retries} tentativas: {url}")
        return None
