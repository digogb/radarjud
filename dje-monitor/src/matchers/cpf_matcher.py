"""
Matcher para busca de CPFs em texto extraído de publicações do DJe.

Suporta múltiplos formatos de CPF e validação de dígitos verificadores.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional


@dataclass
class MatchResult:
    """Resultado de uma busca por CPF."""

    cpf: str  # CPF normalizado (11 dígitos)
    cpf_formatado: str  # CPF no formato 000.000.000-00
    posicao_inicio: int
    posicao_fim: int
    contexto: str  # Texto ao redor da ocorrência
    pagina: Optional[int] = None


class CPFMatcher:
    """
    Busca CPFs em texto, com suporte a múltiplos formatos.

    Formatos reconhecidos:
    - 000.000.000-00 (padrão)
    - 000.000.000/00 (variação)
    - 00000000000 (sem formatação)
    - 000 000 000 00 (com espaços)
    """

    # Padrões de CPF ordenados do mais específico ao mais genérico
    PATTERNS = [
        r"\d{3}\.\d{3}\.\d{3}-\d{2}",  # 000.000.000-00
        r"\d{3}\.\d{3}\.\d{3}/\d{2}",  # 000.000.000/00
        r"(?<!\d)\d{3}\s\d{3}\s\d{3}\s\d{2}(?!\d)",  # 000 000 000 00
    ]

    # Padrão para 11 dígitos seguidos (sem formatação)
    # Precisa de word boundary para não capturar partes de números maiores
    PATTERN_SEM_FORMATO = r"(?<!\d)\d{11}(?!\d)"

    def __init__(self, contexto_chars: int = 500):
        """
        Args:
            contexto_chars: Número de caracteres de contexto ao redor do match.
        """
        self.contexto_chars = contexto_chars

        # Compilar padrão combinado (formatos com pontuação primeiro)
        todos_padroes = self.PATTERNS + [self.PATTERN_SEM_FORMATO]
        self.pattern = re.compile("|".join(f"({p})" for p in todos_padroes))

    @staticmethod
    def normalizar_cpf(cpf: str) -> str:
        """Remove formatação do CPF, mantendo apenas dígitos."""
        return re.sub(r"\D", "", cpf)

    @staticmethod
    def formatar_cpf(cpf: str) -> str:
        """Formata CPF no padrão 000.000.000-00."""
        cpf = re.sub(r"\D", "", cpf)
        if len(cpf) == 11:
            return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
        return cpf

    @staticmethod
    def normalizar_texto(texto: str) -> str:
        """
        Normaliza texto para melhorar detecção de CPF.

        Remove acentos, normaliza espaços e caracteres especiais
        que podem interferir na detecção.
        """
        # Normalizar Unicode
        texto = unicodedata.normalize("NFKD", texto)
        # Substituir caracteres Unicode similares a dígitos
        texto = texto.replace("\u2013", "-").replace("\u2014", "-")
        return texto

    def buscar_cpf(self, texto: str, cpf_alvo: str) -> list[MatchResult]:
        """
        Busca um CPF específico no texto.

        Args:
            texto: Texto onde buscar.
            cpf_alvo: CPF a buscar (qualquer formato).

        Returns:
            Lista de ocorrências encontradas com contexto.
        """
        cpf_normalizado = self.normalizar_cpf(cpf_alvo)
        if len(cpf_normalizado) != 11:
            return []

        texto_normalizado = self.normalizar_texto(texto)
        resultados = []

        for match in self.pattern.finditer(texto_normalizado):
            cpf_encontrado = match.group()
            if self.normalizar_cpf(cpf_encontrado) == cpf_normalizado:
                inicio_ctx = max(0, match.start() - self.contexto_chars)
                fim_ctx = min(len(texto_normalizado), match.end() + self.contexto_chars)

                resultados.append(
                    MatchResult(
                        cpf=cpf_normalizado,
                        cpf_formatado=self.formatar_cpf(cpf_encontrado),
                        posicao_inicio=match.start(),
                        posicao_fim=match.end(),
                        contexto=texto_normalizado[inicio_ctx:fim_ctx].strip(),
                    )
                )

        return resultados

    def buscar_cpf_por_pagina(
        self, paginas: list[tuple[int, str]], cpf_alvo: str
    ) -> list[MatchResult]:
        """
        Busca CPF em texto paginado.

        Args:
            paginas: Lista de (num_pagina, texto).
            cpf_alvo: CPF a buscar.

        Returns:
            Lista de ocorrências com número de página.
        """
        todos_resultados = []

        for num_pagina, texto in paginas:
            resultados = self.buscar_cpf(texto, cpf_alvo)
            for r in resultados:
                r.pagina = num_pagina
            todos_resultados.extend(resultados)

        return todos_resultados

    def buscar_todos_cpfs(self, texto: str) -> list[MatchResult]:
        """
        Encontra todos os CPFs válidos no texto.

        Valida os dígitos verificadores de cada CPF encontrado.

        Args:
            texto: Texto onde buscar.

        Returns:
            Lista de CPFs válidos encontrados.
        """
        texto_normalizado = self.normalizar_texto(texto)
        resultados = []
        cpfs_vistos = set()

        for match in self.pattern.finditer(texto_normalizado):
            cpf_texto = match.group()
            cpf = self.normalizar_cpf(cpf_texto)

            if len(cpf) != 11:
                continue

            if not self.validar_cpf(cpf):
                continue

            inicio_ctx = max(0, match.start() - self.contexto_chars)
            fim_ctx = min(len(texto_normalizado), match.end() + self.contexto_chars)

            chave = (cpf, match.start())
            if chave not in cpfs_vistos:
                cpfs_vistos.add(chave)
                resultados.append(
                    MatchResult(
                        cpf=cpf,
                        cpf_formatado=self.formatar_cpf(cpf),
                        posicao_inicio=match.start(),
                        posicao_fim=match.end(),
                        contexto=texto_normalizado[inicio_ctx:fim_ctx].strip(),
                    )
                )

        return resultados

    @staticmethod
    def validar_cpf(cpf: str) -> bool:
        """
        Valida dígitos verificadores do CPF.

        Args:
            cpf: CPF com 11 dígitos (apenas números).

        Returns:
            True se o CPF é válido.
        """
        cpf = re.sub(r"\D", "", cpf)

        if len(cpf) != 11:
            return False

        # Rejeitar sequências iguais (000.000.000-00, 111.111.111-11, etc.)
        if cpf == cpf[0] * 11:
            return False

        # Primeiro dígito verificador
        soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
        d1 = (soma * 10 % 11) % 10

        # Segundo dígito verificador
        soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
        d2 = (soma * 10 % 11) % 10

        return cpf[-2:] == f"{d1}{d2}"
