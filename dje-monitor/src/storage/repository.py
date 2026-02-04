"""
Repositório para operações de banco de dados.

Fornece interface para criar, buscar e atualizar registros
de CPFs monitorados, diários processados e ocorrências.
"""

import logging
from datetime import date, datetime
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base, CPFMonitorado, DiarioProcessado, Ocorrencia

logger = logging.getLogger(__name__)


class DiarioRepository:
    """Repositório principal do DJE Monitor."""

    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def get_session(self) -> Session:
        """Cria uma nova sessão de banco de dados."""
        return self.SessionLocal()

    # === CPFs Monitorados ===

    def adicionar_cpf(self, cpf: str, nome: str = "") -> CPFMonitorado:
        """Adiciona um CPF para monitoramento."""
        with self.get_session() as session:
            existente = session.query(CPFMonitorado).filter_by(cpf=cpf).first()
            if existente:
                if not existente.ativo:
                    existente.ativo = True
                    existente.atualizado_em = datetime.utcnow()
                    session.commit()
                    session.refresh(existente)
                    logger.info(f"CPF {cpf} reativado para monitoramento")
                session.expunge(existente)
                return existente

            cpf_obj = CPFMonitorado(cpf=cpf, nome=nome, ativo=True)
            session.add(cpf_obj)
            session.commit()
            session.refresh(cpf_obj)
            session.expunge(cpf_obj)
            logger.info(f"CPF {cpf} adicionado para monitoramento")
            return cpf_obj

    def remover_cpf(self, cpf: str) -> bool:
        """Desativa monitoramento de um CPF (soft delete)."""
        with self.get_session() as session:
            cpf_obj = session.query(CPFMonitorado).filter_by(cpf=cpf).first()
            if cpf_obj:
                cpf_obj.ativo = False
                cpf_obj.atualizado_em = datetime.utcnow()
                session.commit()
                logger.info(f"CPF {cpf} desativado")
                return True
            return False

    def listar_cpfs_ativos(self) -> list[CPFMonitorado]:
        """Lista todos os CPFs com monitoramento ativo."""
        with self.get_session() as session:
            results = (
                session.query(CPFMonitorado)
                .filter_by(ativo=True)
                .all()
            )
            for obj in results:
                session.expunge(obj)
            return results

    def obter_cpf(self, cpf: str) -> Optional[CPFMonitorado]:
        """Obtém um CPF monitorado pelo número."""
        with self.get_session() as session:
            obj = session.query(CPFMonitorado).filter_by(cpf=cpf).first()
            if obj:
                session.expunge(obj)
            return obj

    # === Diários Processados ===

    def diario_ja_processado(
        self,
        tribunal: str,
        data_pub: date,
        caderno: str,
        fonte: str,
        hash_arquivo: Optional[str] = None,
    ) -> bool:
        """Verifica se um diário já foi processado."""
        with self.get_session() as session:
            query = session.query(DiarioProcessado).filter(
                DiarioProcessado.tribunal == tribunal,
                DiarioProcessado.data_publicacao == data_pub,
                DiarioProcessado.caderno == caderno,
                DiarioProcessado.fonte == fonte,
            )
            if hash_arquivo:
                query = query.filter(
                    DiarioProcessado.hash_arquivo == hash_arquivo
                )
            return query.first() is not None

    def registrar_diario(
        self,
        tribunal: str,
        fonte: str,
        data_publicacao: date,
        caderno: str,
        caderno_nome: str = "",
        edicao: str = "",
        url_original: str = "",
        caminho_pdf: str = "",
        hash_arquivo: str = "",
        num_paginas: int = 0,
    ) -> DiarioProcessado:
        """Registra um novo diário baixado."""
        with self.get_session() as session:
            # Verificar se já existe
            existente = (
                session.query(DiarioProcessado)
                .filter_by(
                    tribunal=tribunal,
                    data_publicacao=data_publicacao,
                    caderno=caderno,
                    fonte=fonte,
                )
                .first()
            )
            if existente:
                session.expunge(existente)
                return existente

            diario = DiarioProcessado(
                tribunal=tribunal,
                fonte=fonte,
                data_publicacao=data_publicacao,
                caderno=caderno,
                caderno_nome=caderno_nome,
                edicao=edicao,
                url_original=url_original,
                caminho_pdf=caminho_pdf,
                hash_arquivo=hash_arquivo,
                num_paginas=num_paginas,
            )
            session.add(diario)
            session.commit()
            session.refresh(diario)
            session.expunge(diario)
            logger.info(
                f"Diário registrado: {tribunal} {data_publicacao} caderno {caderno}"
            )
            return diario

    def marcar_processado(self, diario_id: int) -> None:
        """Marca um diário como processado."""
        with self.get_session() as session:
            diario = session.get(DiarioProcessado, diario_id)
            if diario:
                diario.processado = True
                diario.processado_em = datetime.utcnow()
                session.commit()

    def marcar_texto_extraido(self, diario_id: int) -> None:
        """Marca que o texto foi extraído do diário."""
        with self.get_session() as session:
            diario = session.get(DiarioProcessado, diario_id)
            if diario:
                diario.texto_extraido = True
                session.commit()

    def listar_diarios_pendentes(self) -> list[DiarioProcessado]:
        """Lista diários que ainda não foram processados."""
        with self.get_session() as session:
            results = (
                session.query(DiarioProcessado)
                .filter_by(processado=False)
                .order_by(DiarioProcessado.data_publicacao.desc())
                .all()
            )
            for obj in results:
                session.expunge(obj)
            return results

    # === Ocorrências ===

    def registrar_ocorrencia(
        self,
        cpf_id: int,
        diario_id: int,
        pagina: Optional[int],
        posicao: int,
        contexto: str,
    ) -> Ocorrencia:
        """Registra uma nova ocorrência de CPF encontrada."""
        with self.get_session() as session:
            ocorrencia = Ocorrencia(
                cpf_monitorado_id=cpf_id,
                diario_id=diario_id,
                pagina=pagina,
                posicao=posicao,
                contexto=contexto,
            )
            session.add(ocorrencia)
            session.commit()
            session.refresh(ocorrencia)
            session.expunge(ocorrencia)
            logger.info(
                f"Ocorrência registrada: CPF {cpf_id} no diário {diario_id} "
                f"(página {pagina})"
            )
            return ocorrencia

    def listar_ocorrencias_nao_notificadas(self) -> list[Ocorrencia]:
        """Lista ocorrências que ainda não foram notificadas."""
        with self.get_session() as session:
            results = (
                session.query(Ocorrencia)
                .filter_by(notificado=False)
                .order_by(Ocorrencia.criado_em.desc())
                .all()
            )
            for obj in results:
                session.expunge(obj)
            return results

    def marcar_notificado(self, ocorrencia_id: int) -> None:
        """Marca uma ocorrência como notificada."""
        with self.get_session() as session:
            ocorrencia = session.get(Ocorrencia, ocorrencia_id)
            if ocorrencia:
                ocorrencia.notificado = True
                ocorrencia.notificado_em = datetime.utcnow()
                session.commit()

    def listar_ocorrencias_por_cpf(
        self, cpf: str, limite: int = 50
    ) -> list[dict]:
        """Lista ocorrências para um CPF específico."""
        with self.get_session() as session:
            results = (
                session.query(Ocorrencia, DiarioProcessado, CPFMonitorado)
                .join(DiarioProcessado, Ocorrencia.diario_id == DiarioProcessado.id)
                .join(
                    CPFMonitorado,
                    Ocorrencia.cpf_monitorado_id == CPFMonitorado.id,
                )
                .filter(CPFMonitorado.cpf == cpf)
                .order_by(Ocorrencia.criado_em.desc())
                .limit(limite)
                .all()
            )

            return [
                {
                    "id": oc.id,
                    "cpf": cpf_m.cpf,
                    "nome": cpf_m.nome,
                    "tribunal": diario.tribunal,
                    "data_publicacao": diario.data_publicacao,
                    "caderno": diario.caderno_nome or diario.caderno,
                    "pagina": oc.pagina,
                    "contexto": oc.contexto,
                    "notificado": oc.notificado,
                    "criado_em": oc.criado_em,
                }
                for oc, diario, cpf_m in results
            ]

    def estatisticas(self) -> dict:
        """Retorna estatísticas do sistema."""
        with self.get_session() as session:
            return {
                "cpfs_monitorados": session.query(CPFMonitorado)
                .filter_by(ativo=True)
                .count(),
                "diarios_processados": session.query(DiarioProcessado)
                .filter_by(processado=True)
                .count(),
                "diarios_pendentes": session.query(DiarioProcessado)
                .filter_by(processado=False)
                .count(),
                "total_ocorrencias": session.query(Ocorrencia).count(),
                "ocorrencias_nao_notificadas": session.query(Ocorrencia)
                .filter_by(notificado=False)
                .count(),
            }
