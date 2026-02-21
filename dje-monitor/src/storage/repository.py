"""
Repositório para operações de banco de dados.

Fornece interface para criar, buscar e atualizar registros
de CPFs monitorados, diários processados e ocorrências.
"""

import json
import logging
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session, sessionmaker, joinedload

from .models import Base, CPFMonitorado, DiarioProcessado, Ocorrencia, PessoaMonitorada, PublicacaoMonitorada, Alerta

logger = logging.getLogger(__name__)


class DiarioRepository:
    """Repositório principal do DJE Monitor."""

    def __init__(self, database_url: str):
        self.engine = create_engine(
            database_url,
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
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

    # ===== Pessoas Monitoradas =====

    def adicionar_pessoa(
        self,
        nome: str,
        cpf: Optional[str] = None,
        tribunal_filtro: Optional[str] = None,
        intervalo_horas: int = 24,
        numero_processo: Optional[str] = None,
        comarca: Optional[str] = None,
        uf: Optional[str] = None,
        data_prazo: Optional[date] = None,
        data_expiracao: Optional[date] = None,
        origem_importacao: Optional[str] = None,
    ) -> PessoaMonitorada:
        """Adiciona uma pessoa para monitoramento.

        Deduplicação: busca por CPF primeiro, depois por nome.
        Se encontrar existente: enriquece campos nulos e reativa se inativo.
        """
        with self.get_session() as session:
            existente = None

            # Busca por CPF (identidade mais forte)
            if cpf:
                existente = (
                    session.query(PessoaMonitorada)
                    .filter(PessoaMonitorada.cpf == cpf)
                    .first()
                )

            # Fallback: busca por nome (case-insensitive)
            if not existente:
                existente = (
                    session.query(PessoaMonitorada)
                    .filter(func.lower(PessoaMonitorada.nome) == nome.lower())
                    .first()
                )

            if existente:
                # Enriquecer campos nulos com dados novos
                if cpf and not existente.cpf:
                    existente.cpf = cpf
                if numero_processo and not existente.numero_processo:
                    existente.numero_processo = numero_processo
                if comarca and not existente.comarca:
                    existente.comarca = comarca
                if uf and not existente.uf:
                    existente.uf = uf
                if data_prazo and not existente.data_prazo:
                    existente.data_prazo = data_prazo
                if data_expiracao and not existente.data_expiracao:
                    existente.data_expiracao = data_expiracao
                if origem_importacao and not existente.origem_importacao:
                    existente.origem_importacao = origem_importacao
                if not existente.ativo:
                    existente.ativo = True
                    existente.proximo_check = datetime.utcnow()
                existente.atualizado_em = datetime.utcnow()
                session.commit()
                session.refresh(existente)
                session.expunge(existente)
                return existente

            pessoa = PessoaMonitorada(
                nome=nome,
                cpf=cpf,
                tribunal_filtro=tribunal_filtro,
                intervalo_horas=intervalo_horas,
                numero_processo=numero_processo,
                comarca=comarca,
                uf=uf,
                data_prazo=data_prazo,
                data_expiracao=data_expiracao,
                origem_importacao=origem_importacao,
                proximo_check=datetime.utcnow(),
            )
            session.add(pessoa)
            session.commit()
            session.refresh(pessoa)
            session.expunge(pessoa)
            logger.info(f"Pessoa adicionada para monitoramento: {nome}")
            return pessoa

    def listar_pessoas(self, apenas_ativas: bool = True) -> list[dict]:
        """Lista pessoas monitoradas com contagem de alertas não lidos."""
        with self.get_session() as session:
            query = session.query(PessoaMonitorada)
            if apenas_ativas:
                query = query.filter_by(ativo=True)
            pessoas = query.order_by(PessoaMonitorada.criado_em.desc()).all()

            result = []
            for p in pessoas:
                alertas_nao_lidos = (
                    session.query(func.count(Alerta.id))
                    .filter(Alerta.pessoa_id == p.id, Alerta.lido == False)
                    .scalar()
                ) or 0
                result.append({
                    "id": p.id,
                    "nome": p.nome,
                    "cpf": p.cpf,
                    "tribunal_filtro": p.tribunal_filtro,
                    "ativo": p.ativo,
                    "intervalo_horas": p.intervalo_horas,
                    "ultimo_check": p.ultimo_check.isoformat() if p.ultimo_check else None,
                    "proximo_check": p.proximo_check.isoformat() if p.proximo_check else None,
                    "total_publicacoes": p.total_publicacoes,
                    "total_alertas_nao_lidos": alertas_nao_lidos,
                    "numero_processo": p.numero_processo,
                    "comarca": p.comarca,
                    "uf": p.uf,
                    "data_prazo": p.data_prazo.isoformat() if p.data_prazo else None,
                    "data_expiracao": p.data_expiracao.isoformat() if p.data_expiracao else None,
                    "origem_importacao": p.origem_importacao,
                    "criado_em": p.criado_em.isoformat(),
                    "atualizado_em": p.atualizado_em.isoformat(),
                })
            return result

    def obter_pessoa(self, pessoa_id: int) -> Optional[dict]:
        """Obtém detalhes de uma pessoa monitorada."""
        with self.get_session() as session:
            p = session.get(PessoaMonitorada, pessoa_id)
            if not p:
                return None
            alertas_nao_lidos = (
                session.query(func.count(Alerta.id))
                .filter(Alerta.pessoa_id == p.id, Alerta.lido == False)
                .scalar()
            ) or 0
            return {
                "id": p.id,
                "nome": p.nome,
                "cpf": p.cpf,
                "tribunal_filtro": p.tribunal_filtro,
                "ativo": p.ativo,
                "intervalo_horas": p.intervalo_horas,
                "ultimo_check": p.ultimo_check.isoformat() if p.ultimo_check else None,
                "proximo_check": p.proximo_check.isoformat() if p.proximo_check else None,
                "total_publicacoes": p.total_publicacoes,
                "total_alertas_nao_lidos": alertas_nao_lidos,
                "numero_processo": p.numero_processo,
                "comarca": p.comarca,
                "uf": p.uf,
                "data_prazo": p.data_prazo.isoformat() if p.data_prazo else None,
                "data_expiracao": p.data_expiracao.isoformat() if p.data_expiracao else None,
                "origem_importacao": p.origem_importacao,
                "criado_em": p.criado_em.isoformat(),
                "atualizado_em": p.atualizado_em.isoformat(),
            }

    def obter_pessoa_orm(self, pessoa_id: int) -> Optional[PessoaMonitorada]:
        """Retorna o objeto ORM PessoaMonitorada (detachado da sessão) ou None."""
        with self.get_session() as session:
            p = session.get(PessoaMonitorada, pessoa_id)
            if not p:
                return None
            session.expunge(p)
            return p

    def desativar_expirados(self) -> int:
        """Desativa pessoas cujo data_expiracao já passou. Retorna quantidade desativada."""
        with self.get_session() as session:
            hoje = date.today()
            expirados = (
                session.query(PessoaMonitorada)
                .filter(
                    PessoaMonitorada.ativo == True,
                    PessoaMonitorada.data_expiracao != None,
                    PessoaMonitorada.data_expiracao < hoje,
                )
                .all()
            )
            for p in expirados:
                p.ativo = False
                p.atualizado_em = datetime.utcnow()
            session.commit()
            if expirados:
                logger.info(f"{len(expirados)} monitoramento(s) expirado(s) desativado(s)")
            return len(expirados)

    def atualizar_pessoa(self, pessoa_id: int, **kwargs) -> Optional[dict]:
        """Atualiza campos de uma pessoa monitorada."""
        campos_permitidos = {
            "nome", "cpf", "tribunal_filtro", "ativo", "intervalo_horas",
            "numero_processo", "comarca", "uf", "data_prazo", "data_expiracao", "origem_importacao",
        }
        with self.get_session() as session:
            p = session.get(PessoaMonitorada, pessoa_id)
            if not p:
                return None
            for campo, valor in kwargs.items():
                if campo in campos_permitidos:
                    setattr(p, campo, valor)
            p.atualizado_em = datetime.utcnow()
            session.commit()
        return self.obter_pessoa(pessoa_id)

    def desativar_pessoa(self, pessoa_id: int) -> bool:
        """Desativa monitoramento de uma pessoa (soft delete)."""
        with self.get_session() as session:
            p = session.get(PessoaMonitorada, pessoa_id)
            if p:
                p.ativo = False
                p.atualizado_em = datetime.utcnow()
                session.commit()
                logger.info(f"Pessoa {pessoa_id} ({p.nome}) desativada")
                return True
            return False

    def pessoas_para_verificar(self) -> list[PessoaMonitorada]:
        """Retorna pessoas ativas cuja hora de verificação já chegou."""
        with self.get_session() as session:
            agora = datetime.utcnow()
            results = (
                session.query(PessoaMonitorada)
                .filter(
                    PessoaMonitorada.ativo == True,
                    (PessoaMonitorada.proximo_check == None) | (PessoaMonitorada.proximo_check <= agora),
                )
                .all()
            )
            for obj in results:
                session.expunge(obj)
            return results

    def pessoas_para_verificar_batch(self, limit: int = 500) -> list[PessoaMonitorada]:
        """Retorna até `limit` pessoas ordenadas por proximo_check para processamento em lote."""
        with self.get_session() as session:
            agora = datetime.utcnow()
            results = (
                session.query(PessoaMonitorada)
                .filter(
                    PessoaMonitorada.ativo == True,
                    (PessoaMonitorada.proximo_check == None) | (PessoaMonitorada.proximo_check <= agora),
                )
                .order_by(PessoaMonitorada.proximo_check.asc().nullsfirst())
                .limit(limit)
                .all()
            )
            for obj in results:
                session.expunge(obj)
            return results

    def atualizar_ultimo_check(self, pessoa_id: int) -> None:
        """Atualiza ultimo_check e calcula proximo_check."""
        with self.get_session() as session:
            p = session.get(PessoaMonitorada, pessoa_id)
            if p:
                agora = datetime.utcnow()
                p.ultimo_check = agora
                p.proximo_check = agora + timedelta(hours=p.intervalo_horas)
                session.commit()

    def atualizar_total_publicacoes(self, pessoa_id: int) -> None:
        """Atualiza contador desnormalizado de publicações, excluindo o processo de referência."""
        import re as _re
        with self.get_session() as session:
            p = session.get(PessoaMonitorada, pessoa_id)
            if not p:
                return

            proc_ref_digits = _re.sub(r"\D", "", p.numero_processo or "")

            # Busca todos os numero_processo das publicações desta pessoa
            numeros = (
                session.query(PublicacaoMonitorada.numero_processo)
                .filter(PublicacaoMonitorada.pessoa_id == pessoa_id)
                .all()
            )

            total = sum(
                1 for (num,) in numeros
                if not (proc_ref_digits and _re.sub(r"\D", "", num or "") == proc_ref_digits)
            )

            p.total_publicacoes = total
            session.commit()

    # ===== Publicações Monitoradas =====

    def publicacao_existe(self, hash_unico: str) -> bool:
        """Verifica se uma publicação já foi registrada (deduplicação)."""
        with self.get_session() as session:
            return (
                session.query(PublicacaoMonitorada)
                .filter_by(hash_unico=hash_unico)
                .first()
            ) is not None

    def registrar_publicacao(
        self,
        pessoa_id: int,
        dados: dict,
        hash_unico: str,
        gerar_alerta: bool = True,
    ) -> PublicacaoMonitorada:
        """
        Registra uma nova publicação encontrada para uma pessoa monitorada.
        Se gerar_alerta=False (first check), não cria alerta.
        """
        with self.get_session() as session:
            pub = PublicacaoMonitorada(
                pessoa_id=pessoa_id,
                hash_unico=hash_unico,
                comunicacao_id=dados.get("id") or dados.get("comunicacao_id"),
                tribunal=dados.get("siglaTribunal") or dados.get("tribunal", ""),
                numero_processo=dados.get("numero_processo") or dados.get("processo", ""),
                data_disponibilizacao=dados.get("data_disponibilizacao", ""),
                orgao=dados.get("nomeOrgao") or dados.get("orgao", ""),
                tipo_comunicacao=dados.get("tipoComunicacao") or dados.get("tipo_comunicacao", ""),
                texto_resumo=dados.get("texto_resumo", "")[:500] if dados.get("texto_resumo") else (dados.get("texto", "")[:500] if dados.get("texto") else ""),
                texto_completo=dados.get("texto", ""),
                link=dados.get("link", ""),
                polos_json=json.dumps(dados.get("polos", {}), ensure_ascii=False),
                destinatarios_json=json.dumps(dados.get("destinatarios", []), ensure_ascii=False),
            )
            session.add(pub)
            session.commit()
            session.refresh(pub)
            session.expunge(pub)
            return pub

    def listar_publicacoes_pessoa(
        self, pessoa_id: int, limit: int = 100, excluir_processo: Optional[str] = None
    ) -> list[dict]:
        """Lista publicações de uma pessoa monitorada agrupadas por número de processo.

        Se excluir_processo for fornecido, omite publicações desse processo (referência de origem).
        Retorna lista de grupos: [{numero_processo, tribunal, total, publicacoes: [...]}]
        Ordenação: grupos e publicações em ordem decrescente de data.
        """
        import re as _re
        from datetime import datetime

        proc_ref_digits = _re.sub(r"\D", "", excluir_processo) if excluir_processo else None

        def _parse_data(s: str):
            """Converte string de data (DD/MM/YYYY ou YYYY-MM-DD) para datetime."""
            if not s:
                return datetime.min
            for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.strptime(s[:10], fmt[:len(s[:10].replace("-", "/").replace("/", "-"))])
                except ValueError:
                    pass
            for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                try:
                    return datetime.strptime(s[:10], fmt)
                except ValueError:
                    continue
            return datetime.min

        with self.get_session() as session:
            pubs = (
                session.query(PublicacaoMonitorada)
                .filter_by(pessoa_id=pessoa_id)
                .order_by(PublicacaoMonitorada.criado_em.desc())
                .limit(limit)
                .all()
            )

            grupos: dict = {}
            for p in pubs:
                # Omitir publicações do processo de referência
                if proc_ref_digits:
                    num_digits = _re.sub(r"\D", "", p.numero_processo or "")
                    if num_digits and num_digits == proc_ref_digits:
                        continue

                pub_dict = {
                    "id": p.id,
                    "tribunal": p.tribunal,
                    "numero_processo": p.numero_processo,
                    "data_disponibilizacao": p.data_disponibilizacao,
                    "orgao": p.orgao,
                    "tipo_comunicacao": p.tipo_comunicacao,
                    "texto_resumo": p.texto_resumo,
                    "link": p.link,
                    "criado_em": p.criado_em.isoformat(),
                }
                key = p.numero_processo or "__sem_processo__"
                if key not in grupos:
                    grupos[key] = {
                        "numero_processo": p.numero_processo,
                        "tribunal": p.tribunal,
                        "publicacoes": [],
                    }
                grupos[key]["publicacoes"].append(pub_dict)

            # Ordenar publicações dentro de cada grupo por data desc (parse DD/MM/YYYY ou YYYY-MM-DD)
            for v in grupos.values():
                v["publicacoes"].sort(
                    key=lambda p: _parse_data(p["data_disponibilizacao"]),
                    reverse=True,
                )

            # Ordenar grupos pela data da publicação mais recente
            result = [
                {
                    "numero_processo": v["numero_processo"],
                    "tribunal": v["tribunal"],
                    "total": len(v["publicacoes"]),
                    "publicacoes": v["publicacoes"],
                }
                for v in grupos.values()
            ]
            result.sort(
                key=lambda g: _parse_data(g["publicacoes"][0]["data_disponibilizacao"] if g["publicacoes"] else ""),
                reverse=True,
            )
            return result

    # ===== Alertas =====

    def registrar_alerta(
        self,
        pessoa_id: int,
        publicacao_id: int,
        tipo: str = "NOVA_PUBLICACAO",
        titulo: str = "",
        descricao: str = "",
    ) -> Alerta:
        """Registra um alerta de nova publicação."""
        with self.get_session() as session:
            alerta = Alerta(
                pessoa_id=pessoa_id,
                publicacao_id=publicacao_id,
                tipo=tipo,
                titulo=titulo,
                descricao=descricao,
            )
            session.add(alerta)
            session.commit()
            session.refresh(alerta)
            session.expunge(alerta)
            return alerta

    def marcar_alerta_notificado(self, alerta_id: int, canal: str) -> None:
        """Marca que o alerta foi enviado por um canal específico (telegram ou email)."""
        with self.get_session() as session:
            a = session.get(Alerta, alerta_id)
            if a:
                if canal == "telegram":
                    a.notificado_telegram = True
                elif canal == "email":
                    a.notificado_email = True
                session.commit()

    def listar_alertas(
        self,
        pessoa_id: Optional[int] = None,
        lido: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Lista alertas com dados da pessoa e publicação."""
        with self.get_session() as session:
            query = (
                session.query(Alerta, PessoaMonitorada, PublicacaoMonitorada)
                .join(PessoaMonitorada, Alerta.pessoa_id == PessoaMonitorada.id)
                .join(PublicacaoMonitorada, Alerta.publicacao_id == PublicacaoMonitorada.id)
            )
            if pessoa_id is not None:
                query = query.filter(Alerta.pessoa_id == pessoa_id)
            if lido is not None:
                query = query.filter(Alerta.lido == lido)
            rows = (
                query.order_by(Alerta.criado_em.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": a.id,
                    "pessoa_id": a.pessoa_id,
                    "pessoa_nome": p.nome,
                    "tipo": a.tipo,
                    "titulo": a.titulo,
                    "descricao": a.descricao,
                    "lido": a.lido,
                    "criado_em": a.criado_em.isoformat(),
                    "lido_em": a.lido_em.isoformat() if a.lido_em else None,
                    "publicacao": {
                        "id": pub.id,
                        "tribunal": pub.tribunal,
                        "numero_processo": pub.numero_processo,
                        "data_disponibilizacao": pub.data_disponibilizacao,
                        "tipo_comunicacao": pub.tipo_comunicacao,
                        "orgao": pub.orgao,
                        "texto_resumo": pub.texto_resumo,
                        "link": pub.link,
                    },
                }
                for a, p, pub in rows
            ]

    def contar_alertas_nao_lidos(self, pessoa_id: Optional[int] = None, tipo: Optional[str] = None) -> int:
        """Conta alertas não lidos, opcionalmente filtrando por pessoa e/ou tipo."""
        with self.get_session() as session:
            query = session.query(func.count(Alerta.id)).filter(Alerta.lido == False)
            if pessoa_id is not None:
                query = query.filter(Alerta.pessoa_id == pessoa_id)
            if tipo is not None:
                query = query.filter(Alerta.tipo == tipo)
            return query.scalar() or 0

    def marcar_alertas_lidos(self, ids: Optional[list[int]] = None, todos: bool = False) -> int:
        """Marca alertas como lidos. Retorna quantidade marcada."""
        with self.get_session() as session:
            query = session.query(Alerta).filter(Alerta.lido == False)
            if not todos and ids:
                query = query.filter(Alerta.id.in_(ids))
            agora = datetime.utcnow()
            count = 0
            for a in query.all():
                a.lido = True
                a.lido_em = agora
                count += 1
            session.commit()
            return count

    # ===== Dashboard =====

    def dashboard_stats(self) -> dict:
        """Retorna estatísticas reais para o dashboard."""
        with self.get_session() as session:
            total_pessoas = (
                session.query(func.count(PessoaMonitorada.id))
                .filter_by(ativo=True)
                .scalar()
            ) or 0
            total_publicacoes = session.query(func.count(PublicacaoMonitorada.id)).scalar() or 0
            alertas_nao_lidos = (
                session.query(func.count(Alerta.id)).filter_by(lido=False).scalar()
            ) or 0
            ultima_sync = (
                session.query(func.max(PessoaMonitorada.ultimo_check)).scalar()
            )
            return {
                "totalProcessos": total_publicacoes,
                "processosMonitorados": total_pessoas,
                "alteracoesNaoVistas": alertas_nao_lidos,
                "ultimaSync": ultima_sync.isoformat() if ultima_sync else None,
            }

    def alertas_recentes_dashboard(self, limit: int = 10) -> list[dict]:
        """Retorna alertas recentes no formato AlteracaoDetectada esperado pelo frontend."""
        alertas = self.listar_alertas(lido=False, limit=limit)
        return [
            {
                "id": str(a["id"]),
                "processoId": a["publicacao"]["numero_processo"] or str(a["pessoa_id"]),
                "tipo": a["tipo"],
                "dadosAnteriores": {},
                "dadosNovos": {
                    "tribunal": a["publicacao"]["tribunal"],
                    "tipo_comunicacao": a["publicacao"]["tipo_comunicacao"],
                    "orgao": a["publicacao"]["orgao"],
                    "pessoa": a["pessoa_nome"],
                },
                "detectadoEm": a["criado_em"],
                "visualizado": a["lido"],
                "processo": {
                    "numeroUnificado": a["publicacao"]["numero_processo"],
                    "tribunal": a["publicacao"]["tribunal"],
                    "partes": [],
                },
            }
            for a in alertas
        ]

    # ===== Oportunidades de Crédito =====

    def buscar_oportunidades(self, dias: int = 30, limit: int = 50) -> list[dict]:
        """Varre publicações recentes procurando sinais de recebimento de valores."""
        from sqlalchemy import or_, and_

        since = datetime.utcnow() - timedelta(days=dias)

        # Padrões de detecção no texto_completo
        p1 = and_(
            PublicacaoMonitorada.texto_completo.ilike('%alvará%'),
            or_(
                PublicacaoMonitorada.texto_completo.ilike('%levantamento%'),
                PublicacaoMonitorada.texto_completo.ilike('%pagamento%'),
            ),
        )
        p2 = PublicacaoMonitorada.texto_completo.ilike('%mandado de levantamento%')
        p3 = or_(
            PublicacaoMonitorada.texto_completo.ilike('%expedição de precatório%'),
            PublicacaoMonitorada.texto_completo.ilike('%expedir precatório%'),
            PublicacaoMonitorada.texto_completo.ilike('%precatório%'),
        )
        p4 = or_(
            PublicacaoMonitorada.texto_completo.ilike('%requisição de pequeno valor%'),
            and_(
                PublicacaoMonitorada.texto_completo.ilike('%RPV%'),
                PublicacaoMonitorada.texto_completo.ilike('%expedir%'),
            ),
        )
        p5 = or_(
            PublicacaoMonitorada.texto_completo.ilike('%homologação de acordo%'),
            PublicacaoMonitorada.texto_completo.ilike('%acordo homologado%'),
        )
        p6 = or_(
            PublicacaoMonitorada.texto_completo.ilike('%desbloqueio%'),
            PublicacaoMonitorada.texto_completo.ilike('%levantamento do bloqueio%'),
            PublicacaoMonitorada.texto_completo.ilike('%bloqueio levantado%'),
        )
        p7 = PublicacaoMonitorada.texto_completo.ilike('%ordem de pagamento%')

        with self.get_session() as session:
            rows = (
                session.query(PublicacaoMonitorada, PessoaMonitorada)
                .join(PessoaMonitorada, PublicacaoMonitorada.pessoa_id == PessoaMonitorada.id)
                .filter(
                    PessoaMonitorada.ativo == True,
                    PublicacaoMonitorada.criado_em >= since,
                    or_(p1, p2, p3, p4, p5, p6, p7),
                )
                .order_by(PublicacaoMonitorada.data_disponibilizacao.desc())
                .limit(limit)
                .all()
            )

            result = []
            for pub, pessoa in rows:
                texto = (pub.texto_completo or "").lower()
                if "mandado de levantamento" in texto:
                    padrao = "mandado de levantamento"
                elif "alvará" in texto and "levantamento" in texto:
                    padrao = "alvará de levantamento"
                elif "alvará" in texto and "pagamento" in texto:
                    padrao = "alvará de pagamento"
                elif "expedição de precatório" in texto or "expedir precatório" in texto:
                    padrao = "expedição de precatório"
                elif "precatório" in texto:
                    padrao = "precatório"
                elif "requisição de pequeno valor" in texto or ("rpv" in texto and "expedir" in texto):
                    padrao = "rpv"
                elif "homologação de acordo" in texto or "acordo homologado" in texto:
                    padrao = "acordo homologado"
                elif "desbloqueio" in texto or "levantamento do bloqueio" in texto or "bloqueio levantado" in texto:
                    padrao = "desbloqueio"
                elif "ordem de pagamento" in texto:
                    padrao = "ordem de pagamento"
                else:
                    padrao = "sinal de recebimento"

                result.append({
                    "id": pub.id,
                    "pessoa_id": pessoa.id,
                    "pessoa_nome": pessoa.nome,
                    "tribunal": pub.tribunal,
                    "numero_processo": pub.numero_processo,
                    "data_disponibilizacao": pub.data_disponibilizacao,
                    "orgao": pub.orgao,
                    "tipo_comunicacao": pub.tipo_comunicacao,
                    "texto_resumo": pub.texto_resumo,
                    "texto_completo": pub.texto_completo,
                    "link": pub.link,
                    "padrao_detectado": padrao,
                    "criado_em": pub.criado_em.isoformat(),
                })
            return result

    def alerta_oportunidade_existe(self, publicacao_id: int) -> bool:
        """Verifica se já existe alerta OPORTUNIDADE_CREDITO para esta publicação (deduplicação)."""
        with self.get_session() as session:
            return (
                session.query(Alerta)
                .filter(
                    Alerta.publicacao_id == publicacao_id,
                    Alerta.tipo == "OPORTUNIDADE_CREDITO",
                )
                .first()
            ) is not None

    # ===== Backfill / Reindexação Semântica =====

    def get_publicacoes_batch(self, offset: int = 0, limit: int = 100) -> list:
        """Retorna batch de publicações para reindexação (mantém ORM detachado)."""
        with self.get_session() as session:
            results = (
                session.query(PublicacaoMonitorada)
                .order_by(PublicacaoMonitorada.id)
                .offset(offset)
                .limit(limit)
                .all()
            )
            for obj in results:
                session.expunge(obj)
            return results

    def get_all_processos_com_publicacoes(self) -> list:
        """Agrupa publicações por numero_processo para indexação de processos."""
        with self.get_session() as session:
            pubs = (
                session.query(PublicacaoMonitorada)
                .filter(PublicacaoMonitorada.numero_processo.isnot(None))
                .order_by(PublicacaoMonitorada.numero_processo)
                .all()
            )
            processos: dict = {}
            for pub in pubs:
                key = pub.numero_processo
                if not key:
                    continue
                if key not in processos:
                    processos[key] = {
                        "numero_processo": key,
                        "tribunal": pub.tribunal,
                        "publicacoes": [],
                    }
                processos[key]["publicacoes"].append(pub.to_dict())

        return list(processos.values())

    def get_distinct_processos_batch(self, offset: int = 0, limit: int = 50) -> list[str]:
        """Retorna lista paginada de numero_processo distintos para backfill de processos."""
        from sqlalchemy import distinct, text as sa_text
        with self.get_session() as session:
            rows = (
                session.query(distinct(PublicacaoMonitorada.numero_processo))
                .filter(PublicacaoMonitorada.numero_processo.isnot(None))
                .order_by(PublicacaoMonitorada.numero_processo)
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [row[0] for row in rows]

    def get_publicacoes_por_processo(self, numero_processo: str) -> dict | None:
        """Retorna todas as publicações de um processo agrupadas em dict para indexação."""
        with self.get_session() as session:
            pubs = (
                session.query(PublicacaoMonitorada)
                .filter(PublicacaoMonitorada.numero_processo == numero_processo)
                .order_by(PublicacaoMonitorada.data_disponibilizacao.desc())
                .all()
            )
            if not pubs:
                return None
            return {
                "numero_processo": numero_processo,
                "tribunal": pubs[0].tribunal,
                "publicacoes": [p.to_dict() for p in pubs],
            }

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
