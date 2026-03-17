"""
Modelos de dados para o cliente de busca do DJEN.

DJESearchParams  — parâmetros de entrada (o que buscar e como filtrar)
DJEComunicacao   — resultado normalizado retornado pela API
DJEPolo          — partes ativo/passivo de um processo
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class DJESearchParams:
    """
    Parâmetros de busca para a API DJEN (comunicaapi.pje.jus.br).

    Ao menos um critério principal deve ser informado:
    nome_parte, numero_processo, cpf_cnpj, nome_advogado ou numero_oab.

    Exemplos de uso::

        # Por nome da parte
        DJESearchParams(nome_parte="MARIA SILVA")

        # Por número do processo
        DJESearchParams(numero_processo="0001234-56.2024.8.06.0001")

        # Por advogado, restrito ao TJCE
        DJESearchParams(nome_advogado="JOSE ANTONIO", sigla_tribunal="TJCE")

        # Por OAB com intervalo de datas
        DJESearchParams(
            numero_oab="12345/CE",
            data_inicio=date(2025, 1, 1),
            data_fim=date(2025, 3, 31),
        )

        # Por CPF/CNPJ
        DJESearchParams(cpf_cnpj="12345678901")
    """

    # --- Critérios de busca (ao menos um obrigatório) ---
    nome_parte: Optional[str] = None
    numero_processo: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    nome_advogado: Optional[str] = None
    numero_oab: Optional[str] = None

    # --- Filtros opcionais ---
    sigla_tribunal: Optional[str] = None
    tipo_comunicacao: Optional[str] = None
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None

    # --- Controle de paginação ---
    itens_por_pagina: int = 100
    max_paginas: int = 50

    def validar(self) -> None:
        """Levanta ValueError se nenhum critério de busca foi fornecido."""
        criterios = [
            self.nome_parte,
            self.numero_processo,
            self.cpf_cnpj,
            self.nome_advogado,
            self.numero_oab,
        ]
        if not any(criterios):
            raise ValueError(
                "Informe ao menos um critério de busca: "
                "nome_parte, numero_processo, cpf_cnpj, nome_advogado ou numero_oab."
            )

    @property
    def filtrar_por_destinatario(self) -> bool:
        """
        Indica se os resultados devem ser filtrados pelo nome do destinatário.

        Só faz sentido filtrar quando a busca é por nome de parte, pois a API
        pode retornar comunicações de homônimos. Para os demais critérios
        (processo, CPF, advogado, OAB) o resultado já é preciso o suficiente.
        """
        return bool(self.nome_parte) and not any([
            self.numero_processo,
            self.cpf_cnpj,
            self.nome_advogado,
            self.numero_oab,
        ])


@dataclass
class DJEPolo:
    """Partes classificadas por polo processual."""

    ativo: list[str] = field(default_factory=list)
    passivo: list[str] = field(default_factory=list)
    outros: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"ativo": self.ativo, "passivo": self.passivo, "outros": self.outros}


@dataclass
class DJEComunicacao:
    """
    Comunicação/publicação retornada pela API DJEN.

    Formato normalizado e independente de produto — pode ser convertida para
    dict via ``to_dict()`` quando necessário para compatibilidade com código legado.
    """

    id: str
    tribunal: str
    numero_processo: str
    data_disponibilizacao: str
    orgao: str
    tipo_comunicacao: str
    texto: str
    link: str
    termo_buscado: str
    fonte: str = "DJEN API"
    meio: str = ""
    polos: DJEPolo = field(default_factory=DJEPolo)
    destinatarios: list[str] = field(default_factory=list)
    raw_data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Dicionário compatível com o formato legado do radarjud."""
        return {
            "id": self.id,
            "tribunal": self.tribunal,
            "processo": self.numero_processo,
            "data_disponibilizacao": self.data_disponibilizacao,
            "orgao": self.orgao,
            "tipo_comunicacao": self.tipo_comunicacao,
            "texto": self.texto,
            "link": self.link,
            "termo_buscado": self.termo_buscado,
            "fonte": self.fonte,
            "meio": self.meio,
            "polos": self.polos.to_dict(),
            "partes": self.destinatarios,
            "raw_data": self.raw_data,
        }
