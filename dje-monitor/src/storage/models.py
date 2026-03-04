"""
Modelos SQLAlchemy para o DJE Monitor.

Define as tabelas para:
- CPFs monitorados
- Diários processados
- Ocorrências encontradas
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


# Roles válidos para usuários
USER_ROLES = ("owner", "admin", "advogado", "estagiario", "leitura")


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    """Tenant (escritório de advocacia) com acesso ao DJE Monitor."""

    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Tenant(slug='{self.slug}', name='{self.name}')>"


class CPFMonitorado(Base):
    """CPFs sendo monitorados pelo sistema."""

    __tablename__ = "cpfs_monitorados"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)
    cpf = Column(String(11), nullable=False, index=True)
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
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)
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
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)
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
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)
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
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)
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


class PadraoOportunidade(Base):
    """Padrão de detecção de oportunidades de crédito configurável pelo cliente."""

    __tablename__ = "padroes_oportunidade"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)
    nome = Column(String(100), nullable=False)       # label exibido na UI (ex: "Alvará de Levantamento")
    expressao = Column(String(200), nullable=False)  # frase buscada via ILIKE (ex: "alvará de levantamento")
    tipo = Column(String(20), nullable=False, default='positivo')  # 'positivo' ou 'negativo'
    ativo = Column(Boolean, default=True)
    ordem = Column(Integer, nullable=True)           # prioridade de detecção (menor = maior prioridade)
    criado_em = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<PadraoOportunidade(nome='{self.nome}', expressao='{self.expressao}', ativo={self.ativo})>"


class ClassificacaoProcesso(Base):
    """Classificação automática (via LLM) do papel da parte monitorada em um processo."""

    __tablename__ = "classificacoes_processo"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)
    pessoa_id = Column(Integer, ForeignKey("pessoas_monitoradas.id"), nullable=False, index=True)
    numero_processo = Column(String(30), nullable=False, index=True)  # normalizado (só dígitos)
    papel = Column(String(20))              # CREDOR | DEVEDOR | INDEFINIDO
    veredicto = Column(String(30))          # CREDITO_IDENTIFICADO | CREDITO_POSSIVEL | SEM_CREDITO
    valor = Column(String(100))             # "R$ 50.000,00" ou "não identificado"
    justificativa = Column(String(500))     # 1 frase explicando a classificação
    total_pubs = Column(Integer, nullable=False)  # para invalidação automática
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pessoa = relationship("PessoaMonitorada")

    __table_args__ = (
        UniqueConstraint("pessoa_id", "numero_processo", name="uq_classif_pessoa_processo"),
    )

    def __repr__(self):
        return f"<ClassificacaoProcesso(pessoa_id={self.pessoa_id}, processo='{self.numero_processo}', papel='{self.papel}')>"


class OportunidadeDescartada(Base):
    """Processo descartado manualmente pelo usuário na página de Oportunidades."""

    __tablename__ = "oportunidades_descartadas"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)
    pessoa_id = Column(Integer, ForeignKey("pessoas_monitoradas.id"), nullable=False, index=True)
    numero_processo = Column(String(50), nullable=False)  # normalizado (só dígitos)
    descartado_em = Column(DateTime, default=datetime.utcnow)

    pessoa = relationship("PessoaMonitorada")

    __table_args__ = (
        UniqueConstraint("pessoa_id", "numero_processo", name="uq_descartada_pessoa_processo"),
    )

    def __repr__(self):
        return f"<OportunidadeDescartada(pessoa_id={self.pessoa_id}, processo='{self.numero_processo}')>"


class Alerta(Base):
    """Alerta gerado quando uma nova publicação é encontrada para uma pessoa monitorada."""

    __tablename__ = "alertas"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)
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


# ===== Autenticação e Usuários =====


class User(Base):
    """Usuário do sistema (membro da equipe do escritório/tenant)."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="leitura")
    is_active = Column(Boolean, default=True)

    # Controle de acesso
    last_login_at = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, default=datetime.utcnow)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    must_change_password = Column(Boolean, default=False)

    # Metadata
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuthAuditLog", back_populates="user", foreign_keys="AuthAuditLog.user_id")

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_user_email_tenant"),
    )

    def __repr__(self):
        return f"<User(email='{self.email}', role='{self.role}', tenant='{self.tenant_id}')>"


class RefreshToken(Base):
    """Refresh tokens com suporte a rotation e detecção de reuso."""

    __tablename__ = "refresh_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False)  # SHA-256
    family_id = Column(String(36), nullable=False, index=True)
    is_revoked = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    replaced_by = Column(String(36), ForeignKey("refresh_tokens.id"), nullable=True)

    user = relationship("User", back_populates="refresh_tokens")

    def __repr__(self):
        return f"<RefreshToken(user_id='{self.user_id}', revoked={self.is_revoked})>"


class AuthAuditLog(Base):
    """Log de auditoria para ações de autenticação e gestão de usuários."""

    __tablename__ = "auth_audit_log"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(50), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="audit_logs", foreign_keys=[user_id])

    def __repr__(self):
        return f"<AuthAuditLog(action='{self.action}', user_id='{self.user_id}')>"
