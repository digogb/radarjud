"""Testes para o módulo CPF Matcher."""

import pytest

from matchers.cpf_matcher import CPFMatcher, MatchResult


class TestCPFMatcher:
    """Testes para a classe CPFMatcher."""

    def setup_method(self):
        self.matcher = CPFMatcher(contexto_chars=100)

    # --- Normalização e Formatação ---

    def test_normalizar_cpf_formatado(self):
        assert CPFMatcher.normalizar_cpf("529.982.247-25") == "52998224725"

    def test_normalizar_cpf_sem_formato(self):
        assert CPFMatcher.normalizar_cpf("52998224725") == "52998224725"

    def test_normalizar_cpf_com_espacos(self):
        assert CPFMatcher.normalizar_cpf("529 982 247 25") == "52998224725"

    def test_formatar_cpf(self):
        assert CPFMatcher.formatar_cpf("52998224725") == "529.982.247-25"

    def test_formatar_cpf_ja_formatado(self):
        assert CPFMatcher.formatar_cpf("529.982.247-25") == "529.982.247-25"

    # --- Validação ---

    def test_validar_cpf_valido(self):
        assert CPFMatcher.validar_cpf("52998224725") is True

    def test_validar_cpf_invalido(self):
        assert CPFMatcher.validar_cpf("12345678901") is False

    def test_validar_cpf_todos_iguais(self):
        assert CPFMatcher.validar_cpf("00000000000") is False
        assert CPFMatcher.validar_cpf("11111111111") is False
        assert CPFMatcher.validar_cpf("99999999999") is False

    def test_validar_cpf_tamanho_errado(self):
        assert CPFMatcher.validar_cpf("1234") is False
        assert CPFMatcher.validar_cpf("") is False
        assert CPFMatcher.validar_cpf("123456789012") is False

    # --- Busca de CPF específico ---

    def test_buscar_cpf_formatado(self, texto_com_cpf, cpf_valido):
        resultados = self.matcher.buscar_cpf(texto_com_cpf, cpf_valido)
        assert len(resultados) >= 1
        assert resultados[0].cpf == cpf_valido

    def test_buscar_cpf_sem_formato(self, texto_com_cpf, cpf_valido):
        resultados = self.matcher.buscar_cpf(texto_com_cpf, cpf_valido)
        # Deve encontrar tanto a versão formatada quanto a sem formato
        assert len(resultados) == 2

    def test_buscar_cpf_nao_encontrado(self, texto_sem_cpf, cpf_valido):
        resultados = self.matcher.buscar_cpf(texto_sem_cpf, cpf_valido)
        assert len(resultados) == 0

    def test_buscar_cpf_contexto(self, texto_com_cpf, cpf_valido):
        resultados = self.matcher.buscar_cpf(texto_com_cpf, cpf_valido)
        assert len(resultados) > 0
        # O contexto deve conter texto ao redor
        assert len(resultados[0].contexto) > len(cpf_valido)

    def test_buscar_cpf_invalido_como_alvo(self):
        resultados = self.matcher.buscar_cpf("qualquer texto", "123")
        assert len(resultados) == 0

    # --- Busca por página ---

    def test_buscar_cpf_por_pagina(self, texto_com_cpf, cpf_valido):
        paginas = [
            (1, "Texto sem CPF na primeira página."),
            (2, texto_com_cpf),
            (3, "Outra página sem CPF."),
        ]

        resultados = self.matcher.buscar_cpf_por_pagina(paginas, cpf_valido)
        assert len(resultados) >= 1
        assert all(r.pagina == 2 for r in resultados)

    # --- Busca de todos os CPFs ---

    def test_buscar_todos_cpfs(self, texto_com_cpf):
        resultados = self.matcher.buscar_todos_cpfs(texto_com_cpf)
        # Deve encontrar pelo menos o CPF válido
        cpfs_encontrados = {r.cpf for r in resultados}
        assert "52998224725" in cpfs_encontrados

    def test_buscar_todos_cpfs_texto_vazio(self):
        resultados = self.matcher.buscar_todos_cpfs("")
        assert len(resultados) == 0

    def test_buscar_todos_cpfs_apenas_invalidos(self):
        texto = "CPF: 000.000.000-00 e outro 111.111.111-11"
        resultados = self.matcher.buscar_todos_cpfs(texto)
        # Sequências iguais devem ser rejeitadas
        assert len(resultados) == 0

    # --- MatchResult ---

    def test_match_result_posicao(self, texto_com_cpf, cpf_valido):
        resultados = self.matcher.buscar_cpf(texto_com_cpf, cpf_valido)
        assert len(resultados) > 0
        for r in resultados:
            assert r.posicao_inicio >= 0
            assert r.posicao_fim > r.posicao_inicio
            assert r.cpf == cpf_valido
            assert r.cpf_formatado == "529.982.247-25"
