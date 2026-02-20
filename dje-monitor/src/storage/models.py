"""
Modelos SQLAlchemy para o DJE Monitor.

Define as tabelas para:
- CPFs monitorados
- Diários processados
- Ocorrências encontradas
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class CPFMonitorado(Base):
    """CPFs sendo monitorados pelo sistema."""

    __tablename__ = "cpfs_monitorados"

    id = Column(Integer, primary_key=True)
    cpf = Column(String(11), unique=True, nullable=False, index=True)
    nome = Column(String(200))
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    ocorrencias = relationship("Ocorrencia", back_populates="cpf_monitorado")

    def __repr__(self):
        return f"<CPFMonitorado(cpf='{self.cpf}', nome='{self.nome}')>"


class DiarioProcessado(Base):
    """Registros de diários já baixados e processados."""

    __tablename__ = "diarios_processados"

    id = Column(Integer, primary_key=True)
    tribunal = Column(String(10), nullable=False, index=True)
    fonte = Column(String(20), nullable=False)  # DJEN, e-SAJ
    data_publicacao = Column(Date, nullable=False, index=True)
    caderno = Column(String(100))
    caderno_nome = Column(String(200))
    edicao = Column(String(50))
    url_original = Column(Text)
    caminho_pdf = Column(Text)
    hash_arquivo = Column(String(64))  # SHA256
    num_paginas = Column(Integer, default=0)
    processado = Column(Boolean, default=False)
    processado_em = Column(DateTime)
    texto_extraido = Column(Boolean, default=False)
    criado_em = Column(DateTime, default=datetime.utcnow)

    ocorrencias = relationship("Ocorrencia", back_populates="diario")

    __table_args__ = (
        UniqueConstraint(
            "tribunal", "data_publicacao", "caderno", "fonte",
            name="uq_diario_tribunal_data_caderno_fonte",
        ),
    )

    def __repr__(self):
        return (
            f"<DiarioProcessado(tribunal='{self.tribunal}', "
            f"data='{self.data_publicacao}', caderno='{self.caderno}')>"
        )


class Ocorrencia(Base):
    """Ocorrências de CPFs encontrados em publicações."""

    __tablename__ = "ocorrencias"

    id = Column(Integer, primary_key=True)
    cpf_monitorado_id = Column(
        Integer, ForeignKey("cpfs_monitorados.id"), nullable=False
    )
    diario_id = Column(
        Integer, ForeignKey("diarios_processados.id"), nullable=False
    )
    pagina = Column(Integer)
    posicao = Column(Integer)
    contexto = Column(Text)
    notificado = Column(Boolean, default=False)
    notificado_em = Column(DateTime)
    criado_em = Column(DateTime, default=datetime.utcnow)

    cpf_monitorado = relationship("CPFMonitorado", back_populates="ocorrencias")
    diario = relationship("DiarioProcessado", back_populates="ocorrencias")

    def __repr__(self):
        return (
            f"<Ocorrencia(cpf='{self.cpf_monitorado_id}', "
            f"diario='{self.diario_id}', pagina={self.pagina})>"
        )


# ===== Monitoramento de Pessoas (via API DJEN por nome) =====


class PessoaMonitorada(Base):
    """Pessoa sendo monitorada por nome no DJe via API DJEN."""

    __tablename__ = "pessoas_monitoradas"

    id = Column(Integer, primary_key=True)
    nome = Column(String(300), nullable=False, index=True)
    cpf = Column(String(14), nullable=True, index=True)  # 11 dígitos CPF ou 14 CNPJ
    tribunal_filtro = Column(String(10), nullable=True)  # None = todos os tribunais
    ativo = Column(Boolean, default=True)
    intervalo_horas = Column(Integer, default=24)
    ultimo_check = Column(DateTime, nullable=True)
    proximo_check = Column(DateTime, nullable=True)
    total_publicacoes = Column(Integer, default=0)
    # Dados de origem (planilha)
    numero_processo = Column(String(30), nullable=True)
    comarca = Column(String(200), nullable=True)
    uf = Column(String(2), nullable=True)
    data_prazo = Column(Date, nullable=True)       # Início do período de monitoramento
    data_expiracao = Column(Date, nullable=True)   # data_prazo + 5 anos
    origem_importacao = Column(String(50), nullable=True)  # "PLANILHA" ou "MANUAL"
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    publicacoes = relationship("PublicacaoMonitorada", back_populates="pessoa", cascade="all, delete-orphan")
    alertas = relationship("Alerta", back_populates="pessoa", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PessoaMonitorada(nome='{self.nome}', ativo={self.ativo})>"


class PublicacaoMonitorada(Base):
    """Publicação encontrada para uma pessoa monitorada. Usada para deduplicação."""

    __tablename__ = "publicacoes_monitoradas"

    id = Column(Integer, primary_key=True)
    pessoa_id = Column(Integer, ForeignKey("pessoas_monitoradas.id"), nullable=False, index=True)
    hash_unico = Column(String(64), unique=True, nullable=False, index=True)
    comunicacao_id = Column(String(100), nullable=True)
    tribunal = Column(String(10))
    numero_processo = Column(String(30), index=True)
    data_disponibilizacao = Column(String(20))
    orgao = Column(String(300))
    tipo_comunicacao = Column(String(50))
    texto_resumo = Column(Text)
    texto_completo = Column(Text)
    link = Column(Text)
    polos_json = Column(Text)        # JSON: {"ativo": [...], "passivo": [...]}
    destinatarios_json = Column(Text)  # JSON: ["nome1", "nome2"]
    criado_em = Column(DateTime, default=datetime.utcnow)

    pessoa = relationship("PessoaMonitorada", back_populates="publicacoes")
    alertas = relationship("Alerta", back_populates="publicacao")

    def to_dict(self) -> dict:
        """Converte para dicionário para uso no embedding service e backfill."""
        import json as _json
        polos = {}
        try:
            polos = _json.loads(self.polos_json or "{}")
        except (ValueError, TypeError):
            pass
        return {
            "id": self.id,
            "pessoa_id": self.pessoa_id,
            "tribunal": self.tribunal or "",
            "numero_processo": self.numero_processo or "",
            "data_disponibilizacao": self.data_disponibilizacao or "",
            "orgao": self.orgao or "",
            "tipo_comunicacao": self.tipo_comunicacao or "",
            "texto_completo": self.texto_completo or "",
            "texto_resumo": self.texto_resumo or "",
            "polos_json": self.polos_json or "{}",
            "polos": polos,
            "link": self.link or "",
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }

    def __repr__(self):
        return f"<PublicacaoMonitorada(processo='{self.numero_processo}', tribunal='{self.tribunal}')>"


class Alerta(Base):
    """Alerta gerado quando uma nova publicação é encontrada para uma pessoa monitorada."""

    __tablename__ = "alertas"

    id = Column(Integer, primary_key=True)
    pessoa_id = Column(Integer, ForeignKey("pessoas_monitoradas.id"), nullable=False, index=True)
    publicacao_id = Column(Integer, ForeignKey("publicacoes_monitoradas.id"), nullable=False)
    tipo = Column(String(50), default="NOVA_PUBLICACAO")
    titulo = Column(String(500))
    descricao = Column(Text)
    lido = Column(Boolean, default=False, index=True)
    notificado_telegram = Column(Boolean, default=False)
    notificado_email = Column(Boolean, default=False)
    criado_em = Column(DateTime, default=datetime.utcnow)
    lido_em = Column(DateTime, nullable=True)

    pessoa = relationship("PessoaMonitorada", back_populates="alertas")
    publicacao = relationship("PublicacaoMonitorada", back_populates="alertas")

    def __repr__(self):
        return f"<Alerta(pessoa_id={self.pessoa_id}, tipo='{self.tipo}', lido={self.lido})>"
