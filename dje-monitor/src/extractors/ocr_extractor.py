"""
Extrator OCR para PDFs escaneados (imagem).

Usa Tesseract com modelo em português para extrair texto
de PDFs que são imagens digitalizadas.
"""

import logging
from pathlib import Path

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


class OCRExtractor:
    """
    OCR para PDFs escaneados (imagem).

    Utiliza Tesseract OCR com modelo em português.
    Detecta automaticamente se o PDF é escaneado.
    """

    def __init__(self, lang: str = "por", dpi: int = 200):
        """
        Args:
            lang: Idioma do Tesseract (padrão: português).
            dpi: Resolução para renderização do PDF (padrão: 200).
        """
        self.lang = lang
        self.dpi = dpi

    def pdf_para_texto(self, pdf_path: str | Path) -> str:
        """
        Converte PDF escaneado para texto via OCR.

        Args:
            pdf_path: Caminho para o arquivo PDF.

        Returns:
            Texto extraído via OCR.
        """
        pdf_path = str(pdf_path)
        logger.info(f"Iniciando OCR para {pdf_path}")

        doc = fitz.open(pdf_path)
        partes = []

        for i, pagina in enumerate(doc, 1):
            try:
                # Renderiza página como imagem
                pix = pagina.get_pixmap(dpi=self.dpi)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                # OCR na imagem
                texto = pytesseract.image_to_string(img, lang=self.lang)
                partes.append(texto)

                if i % 10 == 0:
                    logger.debug(f"OCR: processadas {i}/{len(doc)} páginas")

            except Exception as e:
                logger.warning(f"Erro OCR na página {i}: {e}")
                partes.append("")

        doc.close()
        logger.info(f"OCR concluído: {len(doc)} páginas processadas")
        return "\n".join(partes)

    def pdf_para_texto_por_pagina(
        self, pdf_path: str | Path
    ) -> list[tuple[int, str]]:
        """
        Converte PDF escaneado para texto, retornando por página.

        Returns:
            Lista de tuplas (num_pagina, texto).
        """
        pdf_path = str(pdf_path)
        doc = fitz.open(pdf_path)
        paginas = []

        for i, pagina in enumerate(doc, 1):
            try:
                pix = pagina.get_pixmap(dpi=self.dpi)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                texto = pytesseract.image_to_string(img, lang=self.lang)
                paginas.append((i, texto))
            except Exception as e:
                logger.warning(f"Erro OCR na página {i}: {e}")
                paginas.append((i, ""))

        doc.close()
        return paginas

    def detectar_se_escaneado(self, pdf_path: str | Path) -> bool:
        """
        Detecta se PDF é escaneado (baseado em imagem, pouco texto extraível).

        Heurística: se a média de caracteres por página for menor que 100,
        provavelmente é um PDF escaneado/imagem.

        Args:
            pdf_path: Caminho para o arquivo PDF.

        Returns:
            True se o PDF parece ser escaneado.
        """
        try:
            doc = fitz.open(str(pdf_path))
            total_texto = sum(len(p.get_text().strip()) for p in doc)
            total_paginas = len(doc)
            doc.close()

            if total_paginas == 0:
                return False

            media_chars = total_texto / total_paginas
            is_escaneado = media_chars < 100

            if is_escaneado:
                logger.debug(
                    f"PDF detectado como escaneado: {pdf_path} "
                    f"(média: {media_chars:.0f} chars/página)"
                )

            return is_escaneado

        except Exception as e:
            logger.warning(f"Erro ao detectar tipo de PDF: {e}")
            return False

    def verificar_tesseract(self) -> bool:
        """Verifica se o Tesseract está instalado e acessível."""
        try:
            version = pytesseract.get_tesseract_version()
            logger.info(f"Tesseract versão: {version}")
            return True
        except Exception:
            logger.error(
                "Tesseract não encontrado. Instale com: "
                "sudo apt-get install tesseract-ocr tesseract-ocr-por"
            )
            return False
