"""
Testes unitários do embedding_service.

Os testes unitários fazem mock do modelo e do Qdrant para rodar sem dependências externas.
Os testes de integração (marcados com @pytest.mark.integration) requerem Qdrant rodando.
"""

import json
import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# Adiciona src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestBuildPublicacaoText:
    def test_concatena_campos_basicos(self):
        from services.embedding_service import build_publicacao_text

        pub = {
            "texto_completo": "Sentença proferida nos autos",
            "polos_json": json.dumps({"ativo": ["EMPRESA X"], "passivo": ["JOÃO DA SILVA"]}),
            "orgao": "3ª Vara Cível",
            "tipo_comunicacao": "Intimação",
            "numero_processo": "0001234-56.2024.8.06.0001",
        }
        text = build_publicacao_text(pub)
        assert "Sentença proferida" in text
        assert "EMPRESA X" in text
        assert "JOÃO DA SILVA" in text
        assert "3ª Vara Cível" in text

    def test_usa_polo_ativo_passivo_direto(self):
        from services.embedding_service import build_publicacao_text

        pub = {
            "texto_resumo": "Texto de teste",
            "polo_ativo": "PREFEITURA DE FORTALEZA",
            "polo_passivo": "CONTRIBUINTE",
        }
        text = build_publicacao_text(pub)
        assert "PREFEITURA DE FORTALEZA" in text
        assert "CONTRIBUINTE" in text

    def test_fallback_texto_resumo(self):
        from services.embedding_service import build_publicacao_text

        pub = {"texto_resumo": "Apenas resumo"}
        text = build_publicacao_text(pub)
        assert "Apenas resumo" in text

    def test_publicacao_vazia_retorna_vazio(self):
        from services.embedding_service import build_publicacao_text

        text = build_publicacao_text({})
        assert text == ""

    def test_polos_json_invalido_nao_quebra(self):
        from services.embedding_service import build_publicacao_text

        pub = {
            "texto_completo": "Texto ok",
            "polos_json": "JSON_INVALIDO",
        }
        text = build_publicacao_text(pub)
        assert "Texto ok" in text


class TestBuildProcessoText:
    def test_concatena_publicacoes(self):
        from services.embedding_service import build_processo_text

        proc = {
            "numero_processo": "1234567",
            "tribunal": "TJCE",
            "publicacoes": [
                {"texto_completo": "Pub 1"},
                {"texto_completo": "Pub 2"},
            ],
        }
        text = build_processo_text(proc)
        assert "1234567" in text
        assert "TJCE" in text
        assert "Pub 1" in text
        assert "Pub 2" in text


class TestEncode:
    @patch("services.embedding_service.get_model")
    def test_trunca_para_embedding_dims(self, mock_get_model):
        import numpy as np

        mock_model = MagicMock()
        mock_model.encode.return_value = np.random.rand(768).astype("float32")
        mock_get_model.return_value = mock_model

        with patch("services.embedding_service._get_config") as mock_cfg:
            cfg = MagicMock()
            cfg.embedding_dims = 256
            mock_cfg.return_value = cfg

            from services.embedding_service import encode
            # Resetar singleton para forçar recriação
            import services.embedding_service as es
            es._model = mock_model

            vector = encode("texto de teste")
            assert len(vector) == 256

    @patch("services.embedding_service.get_model")
    def test_prefixo_search_query(self, mock_get_model):
        import numpy as np

        mock_model = MagicMock()
        mock_model.encode.return_value = np.random.rand(768).astype("float32")
        mock_get_model.return_value = mock_model

        with patch("services.embedding_service._get_config") as mock_cfg:
            cfg = MagicMock()
            cfg.embedding_dims = 256
            mock_cfg.return_value = cfg

            import services.embedding_service as es
            es._model = mock_model

            from services.embedding_service import encode
            encode("minha busca", prefix="search_query")

            call_args = mock_model.encode.call_args[0][0]
            assert call_args.startswith("search_query:")

    @patch("services.embedding_service.get_model")
    def test_prefixo_search_document_padrao(self, mock_get_model):
        import numpy as np

        mock_model = MagicMock()
        mock_model.encode.return_value = np.random.rand(768).astype("float32")
        mock_get_model.return_value = mock_model

        with patch("services.embedding_service._get_config") as mock_cfg:
            cfg = MagicMock()
            cfg.embedding_dims = 256
            mock_cfg.return_value = cfg

            import services.embedding_service as es
            es._model = mock_model

            from services.embedding_service import encode
            encode("documento")

            call_args = mock_model.encode.call_args[0][0]
            assert call_args.startswith("search_document:")


class TestSearchPublicacoes:
    @patch("services.embedding_service.get_client")
    @patch("services.embedding_service.encode")
    def test_retorna_lista_formatada(self, mock_encode, mock_get_client):
        mock_encode.return_value = [0.1] * 256

        mock_result = MagicMock()
        mock_result.id = 42
        mock_result.score = 0.85
        mock_result.payload = {"tribunal": "TJCE", "texto_resumo": "execução fiscal"}
        mock_get_client.return_value.search.return_value = [mock_result]

        with patch("services.embedding_service._get_config") as mock_cfg:
            cfg = MagicMock()
            cfg.semantic_max_results = 20
            cfg.semantic_score_threshold = 0.35
            mock_cfg.return_value = cfg

            from services.embedding_service import search_publicacoes
            results = search_publicacoes("execução fiscal")

        assert len(results) == 1
        assert results[0]["pub_id"] == 42
        assert results[0]["score"] == 0.85
        assert results[0]["tribunal"] == "TJCE"

    @patch("services.embedding_service.get_client")
    @patch("services.embedding_service.encode")
    def test_filtro_tribunal_passa_corretamente(self, mock_encode, mock_get_client):
        mock_encode.return_value = [0.1] * 256
        mock_get_client.return_value.search.return_value = []

        with patch("services.embedding_service._get_config") as mock_cfg:
            cfg = MagicMock()
            cfg.semantic_max_results = 20
            cfg.semantic_score_threshold = 0.35
            mock_cfg.return_value = cfg

            from services.embedding_service import search_publicacoes
            search_publicacoes("dívida", tribunal="TJCE")

        call_kwargs = mock_get_client.return_value.search.call_args[1]
        assert call_kwargs["query_filter"] is not None

    @patch("services.embedding_service.get_client")
    @patch("services.embedding_service.encode")
    def test_sem_filtro_passa_none(self, mock_encode, mock_get_client):
        mock_encode.return_value = [0.1] * 256
        mock_get_client.return_value.search.return_value = []

        with patch("services.embedding_service._get_config") as mock_cfg:
            cfg = MagicMock()
            cfg.semantic_max_results = 20
            cfg.semantic_score_threshold = 0.35
            mock_cfg.return_value = cfg

            from services.embedding_service import search_publicacoes
            search_publicacoes("dívida")

        call_kwargs = mock_get_client.return_value.search.call_args[1]
        assert call_kwargs["query_filter"] is None


class TestExtractPolo:
    def test_extrai_polo_ativo_de_json(self):
        from services.embedding_service import _extract_polo

        pub = {"polos_json": json.dumps({"ativo": ["EMPRESA X", "EMPRESA Y"], "passivo": []})}
        assert "EMPRESA X" in _extract_polo(pub, "ativo")
        assert "EMPRESA Y" in _extract_polo(pub, "ativo")

    def test_extrai_polo_de_campo_direto(self):
        from services.embedding_service import _extract_polo

        pub = {"polo_ativo": "MUNICIPIO DE FORTALEZA"}
        assert _extract_polo(pub, "ativo") == "MUNICIPIO DE FORTALEZA"

    def test_retorna_vazio_sem_polos(self):
        from services.embedding_service import _extract_polo

        assert _extract_polo({}, "ativo") == ""
        assert _extract_polo({}, "passivo") == ""


@pytest.mark.integration
class TestEmbeddingIntegration:
    """Testes que requerem Qdrant e modelo rodando (marcados com @pytest.mark.integration)."""

    def test_index_and_search(self):
        from services.embedding_service import (
            ensure_collections,
            index_publicacao,
            search_publicacoes,
        )

        ensure_collections()

        pub = {
            "texto_completo": "Execução fiscal para cobrança de IPTU atrasado do exercício de 2023",
            "polos_json": json.dumps({
                "ativo": ["MUNICÍPIO DE FORTALEZA"],
                "passivo": ["JOSÉ DA SILVA"],
            }),
            "orgao": "3ª Vara de Execuções Fiscais",
            "tipo_comunicacao": "Citação",
            "numero_processo": "0001234-56.2024.8.06.0001",
            "tribunal": "TJCE",
            "pessoa_id": 1,
            "data_disponibilizacao": "2024-06-15",
        }
        index_publicacao(99999, pub)

        results = search_publicacoes("dívida tributária IPTU", tribunal="TJCE")
        assert len(results) > 0
        assert results[0]["pub_id"] == 99999
        assert results[0]["score"] > 0.4
