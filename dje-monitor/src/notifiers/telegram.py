"""
Notificador via Telegram.

Envia alertas quando ocorrências de CPFs monitorados são encontradas
em publicações do DJe.
"""

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class MensagemOcorrencia:
    """Dados para montar a mensagem de notificação."""

    cpf: str
    nome: str
    tribunal: str
    data_publicacao: str
    caderno: str
    pagina: int | None
    contexto: str


class TelegramNotifier:
    """
    Notificador via Telegram Bot API.

    Requer:
    - Bot token (criar via @BotFather)
    - Chat ID do destinatário (grupo ou usuário)
    """

    API_URL = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.client = httpx.Client(timeout=30.0)

    def enviar_ocorrencia(self, ocorrencia: MensagemOcorrencia) -> bool:
        """
        Envia notificação de ocorrência encontrada.

        Args:
            ocorrencia: Dados da ocorrência.

        Returns:
            True se a mensagem foi enviada com sucesso.
        """
        mensagem = self._formatar_mensagem(ocorrencia)
        return self._enviar_mensagem(mensagem)

    def enviar_resumo_diario(
        self, total_diarios: int, total_ocorrencias: int, detalhes: list[dict]
    ) -> bool:
        """
        Envia resumo diário do processamento.

        Args:
            total_diarios: Número de diários processados.
            total_ocorrencias: Número de ocorrências encontradas.
            detalhes: Lista de detalhes das ocorrências.

        Returns:
            True se a mensagem foi enviada com sucesso.
        """
        mensagem = self._formatar_resumo(
            total_diarios, total_ocorrencias, detalhes
        )
        return self._enviar_mensagem(mensagem)

    def testar_conexao(self) -> bool:
        """Testa se o bot está configurado corretamente."""
        try:
            url = self.API_URL.format(token=self.bot_token, method="getMe")
            response = self.client.get(url)
            data = response.json()
            if data.get("ok"):
                bot_name = data["result"]["username"]
                logger.info(f"Telegram bot conectado: @{bot_name}")
                return True
            logger.error(f"Erro ao conectar bot: {data}")
            return False
        except Exception as e:
            logger.error(f"Erro ao testar conexão Telegram: {e}")
            return False

    def _enviar_mensagem(self, texto: str, parse_mode: str = "HTML") -> bool:
        """Envia mensagem via Telegram Bot API."""
        try:
            url = self.API_URL.format(
                token=self.bot_token, method="sendMessage"
            )
            payload = {
                "chat_id": self.chat_id,
                "text": texto,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            }

            response = self.client.post(url, json=payload)
            data = response.json()

            if data.get("ok"):
                logger.info("Mensagem Telegram enviada com sucesso")
                return True

            logger.error(f"Erro ao enviar mensagem Telegram: {data}")
            return False

        except Exception as e:
            logger.error(f"Erro ao enviar mensagem Telegram: {e}")
            return False

    def _formatar_mensagem(self, oc: MensagemOcorrencia) -> str:
        """Formata mensagem de ocorrência para Telegram."""
        # Limitar contexto para não exceder limite do Telegram
        contexto = oc.contexto[:500] if oc.contexto else "N/A"
        # Escapar caracteres HTML
        contexto = (
            contexto.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        pagina_info = f"Página {oc.pagina}" if oc.pagina else "N/A"

        return (
            f"🔔 <b>Publicação encontrada no DJe!</b>\n\n"
            f"📋 <b>CPF:</b> {oc.cpf}\n"
            f"👤 <b>Nome:</b> {oc.nome or 'N/A'}\n"
            f"🏛 <b>Tribunal:</b> {oc.tribunal}\n"
            f"📅 <b>Data:</b> {oc.data_publicacao}\n"
            f"📑 <b>Caderno:</b> {oc.caderno}\n"
            f"📄 <b>Local:</b> {pagina_info}\n\n"
            f"📝 <b>Trecho:</b>\n"
            f"<pre>{contexto}</pre>"
        )

    def _formatar_resumo(
        self, total_diarios: int, total_ocorrencias: int, detalhes: list[dict]
    ) -> str:
        """Formata resumo diário."""
        msg = (
            f"📊 <b>Resumo do Monitoramento DJe</b>\n\n"
            f"📰 Diários processados: {total_diarios}\n"
            f"🔍 Ocorrências encontradas: {total_ocorrencias}\n"
        )

        if detalhes:
            msg += "\n<b>Detalhes:</b>\n"
            for d in detalhes[:10]:  # Limitar a 10 itens
                msg += (
                    f"• {d.get('cpf', 'N/A')} - "
                    f"{d.get('tribunal', 'N/A')} "
                    f"({d.get('data_publicacao', 'N/A')})\n"
                )

            if len(detalhes) > 10:
                msg += f"\n... e mais {len(detalhes) - 10} ocorrências."

        if total_ocorrencias == 0:
            msg += "\n✅ Nenhuma ocorrência encontrada hoje."

        return msg

    def __del__(self):
        try:
            self.client.close()
        except Exception:
            pass
