"""Testes para o módulo de Storage (models e repository)."""

from datetime import date

import pytest

from storage.repository import DiarioRepository


class TestDiarioRepository:
    """Testes para o repositório de dados.
    Requer DJE_TEST_DATABASE_URL configurado no ambiente.
    """

    @pytest.fixture(autouse=True)
    def setup_repo(self, db_url):
        self.repo = DiarioRepository(db_url)

    # --- CPFs Monitorados ---

    def test_adicionar_cpf(self):
        cpf = self.repo.adicionar_cpf("52998224725", nome="Fulano")
        assert cpf.cpf == "52998224725"
        assert cpf.nome == "Fulano"
        assert cpf.ativo is True

    def test_adicionar_cpf_duplicado(self):
        self.repo.adicionar_cpf("52998224725", nome="Fulano")
        cpf2 = self.repo.adicionar_cpf("52998224725", nome="Outro Nome")
        # Não deve duplicar
        assert cpf2.cpf == "52998224725"

    def test_remover_cpf(self):
        self.repo.adicionar_cpf("52998224725")
        result = self.repo.remover_cpf("52998224725")
        assert result is True

        cpfs = self.repo.listar_cpfs_ativos()
        assert len(cpfs) == 0

    def test_remover_cpf_inexistente(self):
        result = self.repo.remover_cpf("00000000000")
        assert result is False

    def test_reativar_cpf(self):
        self.repo.adicionar_cpf("52998224725")
        self.repo.remover_cpf("52998224725")

        # Readicionar deve reativar
        cpf = self.repo.adicionar_cpf("52998224725")
        assert cpf.ativo is True

    def test_listar_cpfs_ativos(self):
        self.repo.adicionar_cpf("52998224725", nome="Pessoa A")
        self.repo.adicionar_cpf("11144477735", nome="Pessoa B")
        self.repo.adicionar_cpf("00000000000", nome="Pessoa C")
        self.repo.remover_cpf("00000000000")

        cpfs = self.repo.listar_cpfs_ativos()
        assert len(cpfs) == 2

    # --- Diários Processados ---

    def test_registrar_diario(self):
        diario = self.repo.registrar_diario(
            tribunal="TJCE",
            fonte="DJEN",
            data_publicacao=date(2025, 1, 15),
            caderno="3",
            caderno_nome="Judicial 1ª Instância",
            edicao="1234",
            url_original="https://example.com/diario.pdf",
        )
        assert diario.tribunal == "TJCE"
        assert diario.processado is False

    def test_diario_ja_processado_nao(self):
        result = self.repo.diario_ja_processado(
            "TJCE", date(2025, 1, 15), "3", "DJEN"
        )
        assert result is False

    def test_diario_ja_processado_sim(self):
        self.repo.registrar_diario(
            tribunal="TJCE",
            fonte="DJEN",
            data_publicacao=date(2025, 1, 15),
            caderno="3",
        )
        result = self.repo.diario_ja_processado(
            "TJCE", date(2025, 1, 15), "3", "DJEN"
        )
        assert result is True

    def test_registrar_diario_duplicado(self):
        d1 = self.repo.registrar_diario(
            tribunal="TJCE",
            fonte="DJEN",
            data_publicacao=date(2025, 1, 15),
            caderno="3",
        )
        d2 = self.repo.registrar_diario(
            tribunal="TJCE",
            fonte="DJEN",
            data_publicacao=date(2025, 1, 15),
            caderno="3",
        )
        assert d1.id == d2.id

    def test_marcar_processado(self):
        diario = self.repo.registrar_diario(
            tribunal="TJCE",
            fonte="DJEN",
            data_publicacao=date(2025, 1, 15),
            caderno="3",
        )
        self.repo.marcar_processado(diario.id)

        result = self.repo.diario_ja_processado(
            "TJCE", date(2025, 1, 15), "3", "DJEN"
        )
        assert result is True

    def test_listar_diarios_pendentes(self):
        self.repo.registrar_diario(
            tribunal="TJCE",
            fonte="DJEN",
            data_publicacao=date(2025, 1, 15),
            caderno="3",
        )
        self.repo.registrar_diario(
            tribunal="TJCE",
            fonte="DJEN",
            data_publicacao=date(2025, 1, 15),
            caderno="2",
        )

        pendentes = self.repo.listar_diarios_pendentes()
        assert len(pendentes) == 2

    # --- Ocorrências ---

    def test_registrar_ocorrencia(self):
        cpf = self.repo.adicionar_cpf("52998224725")
        diario = self.repo.registrar_diario(
            tribunal="TJCE",
            fonte="DJEN",
            data_publicacao=date(2025, 1, 15),
            caderno="3",
        )

        oc = self.repo.registrar_ocorrencia(
            cpf_id=cpf.id,
            diario_id=diario.id,
            pagina=42,
            posicao=1500,
            contexto="...texto ao redor do CPF...",
        )
        assert oc.pagina == 42
        assert oc.notificado is False

    def test_listar_ocorrencias_nao_notificadas(self):
        cpf = self.repo.adicionar_cpf("52998224725")
        diario = self.repo.registrar_diario(
            tribunal="TJCE",
            fonte="DJEN",
            data_publicacao=date(2025, 1, 15),
            caderno="3",
        )

        self.repo.registrar_ocorrencia(
            cpf_id=cpf.id,
            diario_id=diario.id,
            pagina=1,
            posicao=100,
            contexto="contexto 1",
        )
        self.repo.registrar_ocorrencia(
            cpf_id=cpf.id,
            diario_id=diario.id,
            pagina=5,
            posicao=500,
            contexto="contexto 2",
        )

        nao_notificadas = self.repo.listar_ocorrencias_nao_notificadas()
        assert len(nao_notificadas) == 2

    def test_marcar_notificado(self):
        cpf = self.repo.adicionar_cpf("52998224725")
        diario = self.repo.registrar_diario(
            tribunal="TJCE",
            fonte="DJEN",
            data_publicacao=date(2025, 1, 15),
            caderno="3",
        )

        oc = self.repo.registrar_ocorrencia(
            cpf_id=cpf.id,
            diario_id=diario.id,
            pagina=1,
            posicao=100,
            contexto="contexto",
        )

        self.repo.marcar_notificado(oc.id)

        nao_notificadas = self.repo.listar_ocorrencias_nao_notificadas()
        assert len(nao_notificadas) == 0

    # --- Estatísticas ---

    def test_estatisticas_vazio(self):
        stats = self.repo.estatisticas()
        assert stats["cpfs_monitorados"] == 0
        assert stats["diarios_processados"] == 0
        assert stats["total_ocorrencias"] == 0

    def test_estatisticas_com_dados(self):
        cpf = self.repo.adicionar_cpf("52998224725")
        diario = self.repo.registrar_diario(
            tribunal="TJCE",
            fonte="DJEN",
            data_publicacao=date(2025, 1, 15),
            caderno="3",
        )
        self.repo.marcar_processado(diario.id)
        self.repo.registrar_ocorrencia(
            cpf_id=cpf.id,
            diario_id=diario.id,
            pagina=1,
            posicao=100,
            contexto="contexto",
        )

        stats = self.repo.estatisticas()
        assert stats["cpfs_monitorados"] == 1
        assert stats["diarios_processados"] == 1
        assert stats["total_ocorrencias"] == 1
