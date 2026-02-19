"""Testes para o módulo de configuração."""

import os

import pytest

from config import Config


_TEST_DB_URL = "postgresql://test:test@localhost:5432/djedb_test"


class TestConfig:
    """Testes para a classe Config."""

    @pytest.fixture(autouse=True)
    def set_db_url(self, monkeypatch):
        """Garante que DJE_DATABASE_URL está definido em todos os testes desta classe."""
        monkeypatch.setenv("DJE_DATABASE_URL", _TEST_DB_URL)

    def test_config_padrao(self, tmp_path):
        config = Config(base_dir=tmp_path)
        assert config.tribunal == "TJCE"
        assert config.usar_djen is True
        assert config.usar_esaj is True
        assert config.dias_retroativos == 3
        assert config.modo_scheduler is False

    def test_config_diretorio_dados_criado(self, tmp_path):
        config = Config(base_dir=tmp_path)
        assert config.pdf_dir.exists()

    def test_config_database_url_obrigatorio(self, tmp_path, monkeypatch):
        monkeypatch.delenv("DJE_DATABASE_URL", raising=False)
        with pytest.raises(ValueError, match="DJE_DATABASE_URL"):
            Config(base_dir=tmp_path)

    def test_config_telegram_desabilitado(self, tmp_path):
        config = Config(base_dir=tmp_path)
        assert config.telegram_habilitado is False

    def test_config_email_desabilitado(self, tmp_path):
        config = Config(base_dir=tmp_path)
        assert config.email_habilitado is False

    def test_config_cpfs_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DJE_CPFS_MONITORADOS", "52998224725,11144477735")
        config = Config(base_dir=tmp_path)
        assert len(config.cpfs_monitorados) == 2
        assert "52998224725" in config.cpfs_monitorados
