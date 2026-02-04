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
