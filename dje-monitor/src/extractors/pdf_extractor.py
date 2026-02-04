"""
Extrator de texto de PDFs do DJe.

Usa PyMuPDF (fitz) como extrator primário e pdfplumber como fallback.
"""

import logging
from pathlib import Path

import fitz  # PyMuPDF
import pdfplumber

logger = logging.getLogger(__name__)


class PDFExtractor:
    """
    Extrai texto de PDFs do DJe.

    Estratégia:
    1. Tenta PyMuPDF (mais rápido, melhor para PDFs digitais)
    2. Fallback para pdfplumber (melhor layout em alguns casos)
    """

    def extrair_texto(self, pdf_path: str | Path) -> str:
        """
        Extrai texto completo do PDF.

        Args:
            pdf_path: Caminho para o arquivo PDF.

        Returns:
            Texto extraído do PDF.
        """
        pdf_path = str(pdf_path)

        try:
            texto = self._extrair_com_pymupdf(pdf_path)
            if texto.strip():
                return texto
        except Exception as e:
            logger.warning(f"PyMuPDF falhou para {pdf_path}: {e}")

        try:
            texto = self._extrair_com_pdfplumber(pdf_path)
            if texto.strip():
                return texto
        except Exception as e:
            logger.warning(f"pdfplumber falhou para {pdf_path}: {e}")

        logger.error(f"Nenhum extrator conseguiu extrair texto de {pdf_path}")
        return ""

    def extrair_por_pagina(self, pdf_path: str | Path) -> list[tuple[int, str]]:
        """
        Extrai texto página a página.

        Args:
            pdf_path: Caminho para o arquivo PDF.

        Returns:
            Lista de tuplas (num_pagina, texto).
        """
        pdf_path = str(pdf_path)
        paginas = []

        try:
            doc = fitz.open(pdf_path)
            for i, pagina in enumerate(doc, 1):
                texto = pagina.get_text()
                paginas.append((i, texto))
            doc.close()
        except Exception as e:
            logger.warning(f"PyMuPDF falhou na extração por página: {e}")
            try:
                paginas = self._extrair_paginas_pdfplumber(pdf_path)
            except Exception as e2:
                logger.error(f"Fallback pdfplumber também falhou: {e2}")

        return paginas

    def contar_paginas(self, pdf_path: str | Path) -> int:
        """Retorna o número de páginas do PDF."""
        try:
            doc = fitz.open(str(pdf_path))
            n = len(doc)
            doc.close()
            return n
        except Exception:
            return 0

    def extrair_metadata(self, pdf_path: str | Path) -> dict:
        """Extrai metadados do PDF."""
        try:
            doc = fitz.open(str(pdf_path))
            metadata = doc.metadata or {}
            metadata["num_paginas"] = len(doc)
            doc.close()
            return metadata
        except Exception as e:
            logger.warning(f"Erro ao extrair metadados: {e}")
            return {}

    def _extrair_com_pymupdf(self, pdf_path: str) -> str:
        """Extração usando PyMuPDF (fitz)."""
        doc = fitz.open(pdf_path)
        partes = []
        for pagina in doc:
            texto = pagina.get_text()
            if texto:
                partes.append(texto)
        doc.close()
        return "\n".join(partes)

    def _extrair_com_pdfplumber(self, pdf_path: str) -> str:
        """Extração usando pdfplumber."""
        partes = []
        with pdfplumber.open(pdf_path) as pdf:
            for pagina in pdf.pages:
                texto = pagina.extract_text()
                if texto:
                    partes.append(texto)
        return "\n".join(partes)

    def _extrair_paginas_pdfplumber(
        self, pdf_path: str
    ) -> list[tuple[int, str]]:
        """Extrai páginas usando pdfplumber como fallback."""
        paginas = []
        with pdfplumber.open(pdf_path) as pdf:
            for i, pagina in enumerate(pdf.pages, 1):
                texto = pagina.extract_text() or ""
                paginas.append((i, texto))
        return paginas
