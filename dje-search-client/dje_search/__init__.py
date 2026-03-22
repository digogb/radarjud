"""
dje-search-client
=================

Cliente reutilizável para a API de busca do DJEN
(Diário da Justiça Eletrônico Nacional — comunicaapi.pje.jus.br).

Exportações principais::

    from dje_search import DJESearchClient, DJESearchParams, DJEComunicacao, DJEPolo, DJEAdvogado
"""

from .client import DJESearchClient
from .models import DJEAdvogado, DJEComunicacao, DJEPolo, DJESearchParams

__all__ = [
    "DJESearchClient",
    "DJESearchParams",
    "DJEComunicacao",
    "DJEPolo",
    "DJEAdvogado",
]
