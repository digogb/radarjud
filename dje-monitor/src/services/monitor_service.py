"""
Serviço de Monitoramento de Pessoas.

Responsável por:
- Verificar periodicamente novas publicações para pessoas monitoradas
- Detectar publicações inéditas e criar alertas
- Enviar notificações via Telegram/Email quando configurados
- Executar o first check ao cadastrar uma pessoa (sem alertas)
"""

import logging
from datetime import date
from typing import Optional

from collectors.djen_collector import DJENCollector
from notifiers.telegram import TelegramNotifier, MensagemOcorrencia
from notifiers.email_notifier import EmailNotifier
from storage.repository import DiarioRepository
from storage.models import PessoaMonitorada
from utils.data_normalizer import gerar_hash_publicacao

logger = logging.getLogger(__name__)


class MonitorService:
    """Serviço de monitoramento de pessoas no DJe via API DJEN."""

    def __init__(self, repo: DiarioRepository, config):
        self.repo = repo
        self.config = config
        # Collector padrão — a busca por nome no DJEN é nacional
        self.collector = DJENCollector(tribunal=config.tribunal)
        self.notifiers = self._init_notifiers()

    def _init_notifiers(self) -> list:
        notifiers = []
        if self.config.telegram_habilitado:
            notifiers.append(
                TelegramNotifier(
                    bot_token=self.config.telegram_bot_token,
                    chat_id=self.config.telegram_chat_id,
                )
            )
        if self.config.email_habilitado:
            notifiers.append(
                EmailNotifier(
                    smtp_host=self.config.smtp_host,
                    smtp_port=self.config.smtp_port,
                    smtp_user=self.config.smtp_user,
                    smtp_password=self.config.smtp_password,
                    destinatarios=self.config.email_destinatarios,
                )
            )
        return notifiers

    def first_check(self, pessoa_id: int, nome: str, tribunal_filtro: Optional[str] = None) -> int:
        """
        Executa busca inicial ao cadastrar uma pessoa.
        Salva publicações existentes como 'conhecidas' SEM gerar alertas.
        Retorna quantidade de publicações encontradas.
        """
        logger.info(f"First check para: {nome}")
        resultados = self._buscar(nome, tribunal_filtro)
        novos = 0
        for item in resultados:
            hash_pub = gerar_hash_publicacao(item)
            if self.repo.publicacao_existe(hash_pub):
                continue
            self.repo.registrar_publicacao(
                pessoa_id=pessoa_id,
                dados=item,
                hash_unico=hash_pub,
                gerar_alerta=False,
            )
            novos += 1

        self.repo.atualizar_ultimo_check(pessoa_id)
        self.repo.atualizar_total_publicacoes(pessoa_id)
        logger.info(f"First check concluído para {nome}: {novos} publicações salvas")
        return novos

    def verificar_todas_pessoas(self) -> None:
        """
        Fallback sequencial — usado apenas quando Dramatiq não está disponível.
        Em produção, o scheduler da API enfileira agendar_verificacoes_task.send()
        e o worker Dramatiq processa cada pessoa em paralelo.
        """
        try:
            expirados = self.repo.desativar_expirados()
            if expirados > 0:
                logger.info(f"{expirados} monitoramento(s) expirado(s) desativado(s)")
        except Exception as e:
            logger.error(f"Erro ao desativar expirados: {e}")

        pessoas = self.repo.pessoas_para_verificar()
        if not pessoas:
            logger.debug("Nenhuma pessoa para verificar no momento")
            return

        logger.info(f"Iniciando verificação sequencial de {len(pessoas)} pessoa(s)")
        for pessoa in pessoas:
            try:
                novos = self.verificar_pessoa(pessoa)
                logger.info(f"Pessoa '{pessoa.nome}': {novos} nova(s) publicação(ões)")
            except Exception as e:
                logger.error(f"Erro ao verificar {pessoa.nome}: {e}", exc_info=True)
            finally:
                self.repo.atualizar_ultimo_check(pessoa.id)

    def verificar_pessoa(self, pessoa: PessoaMonitorada) -> int:
        """
        Verifica uma pessoa específica buscando novas publicações.
        Retorna quantidade de publicações novas encontradas.
        """
        resultados = self._buscar(pessoa.nome, pessoa.tribunal_filtro)
        novos = 0

        for item in resultados:
            hash_pub = gerar_hash_publicacao(item)
            if self.repo.publicacao_existe(hash_pub):
                continue

            # Nova publicação encontrada
            pub = self.repo.registrar_publicacao(
                pessoa_id=pessoa.id,
                dados=item,
                hash_unico=hash_pub,
            )

            titulo = self._montar_titulo(item)
            descricao = self._montar_descricao(item)

            alerta = self.repo.registrar_alerta(
                pessoa_id=pessoa.id,
                publicacao_id=pub.id,
                tipo="NOVA_PUBLICACAO",
                titulo=titulo,
                descricao=descricao,
            )

            self._notificar(pessoa, item, alerta.id)
            novos += 1

        self.repo.atualizar_total_publicacoes(pessoa.id)
        return novos

    def _buscar(self, nome: str, tribunal_filtro: Optional[str] = None) -> list[dict]:
        """Executa busca na API DJEN e retorna resultados normalizados."""
        hoje = date.today()
        try:
            resultados = self.collector.buscar_por_nome(
                nome, hoje, hoje, max_paginas=self.config.monitor_max_paginas
            )
        except Exception as e:
            logger.error(f"Erro na busca DJEN para '{nome}': {e}")
            return []

        if tribunal_filtro:
            resultados = [
                r for r in resultados
                if (r.get("siglaTribunal") or r.get("tribunal", "")).upper() == tribunal_filtro.upper()
            ]

        return resultados

    def _montar_titulo(self, item: dict) -> str:
        tipo = item.get("tipoComunicacao") or item.get("tipo_comunicacao") or "COMUNICACAO"
        tribunal = item.get("siglaTribunal") or item.get("tribunal", "")
        processo = item.get("numero_processo") or item.get("processo", "")
        partes = [tribunal, tipo]
        if processo:
            partes.append(processo)
        return " | ".join(filter(None, partes))

    def _montar_descricao(self, item: dict) -> str:
        orgao = item.get("nomeOrgao") or item.get("orgao", "")
        data = item.get("data_disponibilizacao", "")
        texto = item.get("texto_resumo") or item.get("texto", "")
        linhas = []
        if orgao:
            linhas.append(f"Órgão: {orgao}")
        if data:
            linhas.append(f"Data: {data}")
        if texto:
            linhas.append(f"\n{texto[:400]}")
        return "\n".join(linhas)

    def _notificar(self, pessoa: PessoaMonitorada, item: dict, alerta_id: int) -> None:
        """Envia notificações externas (Telegram/Email) para uma nova publicação."""
        if not self.notifiers:
            return

        msg = MensagemOcorrencia(
            cpf=pessoa.cpf or "",
            nome=pessoa.nome,
            tribunal=item.get("siglaTribunal") or item.get("tribunal", ""),
            data_publicacao=item.get("data_disponibilizacao", ""),
            caderno=item.get("nomeOrgao") or item.get("orgao", ""),
            pagina=None,
            contexto=(item.get("texto_resumo") or item.get("texto", ""))[:500],
        )

        for notifier in self.notifiers:
            try:
                if isinstance(notifier, TelegramNotifier):
                    if notifier.enviar_ocorrencia(msg):
                        self.repo.marcar_alerta_notificado(alerta_id, "telegram")
                elif isinstance(notifier, EmailNotifier):
                    notifier.enviar_ocorrencia(
                        cpf=msg.cpf,
                        nome=msg.nome,
                        tribunal=msg.tribunal,
                        data_publicacao=msg.data_publicacao,
                        caderno=msg.caderno,
                        pagina=None,
                        contexto=msg.contexto,
                    )
                    self.repo.marcar_alerta_notificado(alerta_id, "email")
            except Exception as e:
                logger.error(f"Erro ao enviar notificação via {type(notifier).__name__}: {e}")
