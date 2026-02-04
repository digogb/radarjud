"""Fixtures compartilhadas para testes."""

import sys
from pathlib import Path

import pytest

# Adicionar src ao path para imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def cpf_valido():
    """CPF válido para testes (gerado para teste)."""
    return "52998224725"


@pytest.fixture
def cpf_valido_formatado():
    """CPF válido formatado."""
    return "529.982.247-25"


@pytest.fixture
def cpf_invalido():
    """CPF inválido para testes."""
    return "12345678901"


@pytest.fixture
def texto_com_cpf():
    """Texto simulando publicação do DJe contendo CPF."""
    return """
    PODER JUDICIÁRIO
    TRIBUNAL DE JUSTIÇA DO ESTADO DO CEARÁ
    DIÁRIO DA JUSTIÇA ELETRÔNICO

    Processo: 0001234-56.2024.8.06.0001
    Classe: Ação de Execução Fiscal
    Assunto: IPTU/Imposto Predial e Territorial Urbano

    DECISÃO

    Vistos etc.

    Trata-se de ação de execução fiscal movida pelo Município de Fortaleza
    em face de FULANO DE TAL, CPF 529.982.247-25, visando à cobrança de
    crédito tributário referente ao IPTU dos exercícios de 2020 a 2023.

    Ante o exposto, DETERMINO a citação do executado FULANO DE TAL,
    inscrito no CPF sob o nº 52998224725, para que pague a dívida no
    prazo de 5 (cinco) dias, acrescida de juros, multa e demais encargos.

    Fortaleza/CE, 15 de janeiro de 2025.

    Juiz de Direito
    """


@pytest.fixture
def texto_sem_cpf():
    """Texto simulando publicação sem CPF."""
    return """
    PODER JUDICIÁRIO
    TRIBUNAL DE JUSTIÇA DO ESTADO DO CEARÁ
    DIÁRIO DA JUSTIÇA ELETRÔNICO

    PORTARIA Nº 001/2025

    O Presidente do Tribunal de Justiça do Estado do Ceará, no uso de
    suas atribuições legais, resolve designar o servidor JOSE DA SILVA
    para exercer a função de assessor do gabinete.

    Fortaleza/CE, 10 de janeiro de 2025.
    """


@pytest.fixture
def db_url(tmp_path):
    """URL de banco de dados SQLite temporário para testes."""
    return f"sqlite:///{tmp_path / 'test.sqlite'}"
