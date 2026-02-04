"""
Notificador via Email (SMTP).

Envia alertas por email quando ocorrências de CPFs monitorados
são encontradas em publicações do DJe.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


class EmailNotifier:
    """
    Notificador via Email usando SMTP.

    Suporta SMTP com TLS (porta 587) e SSL (porta 465).
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        destinatarios: list[str],
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.destinatarios = destinatarios

    def enviar_ocorrencia(
        self,
        cpf: str,
        nome: str,
        tribunal: str,
        data_publicacao: str,
        caderno: str,
        pagina: int | None,
        contexto: str,
    ) -> bool:
        """Envia email de notificação de ocorrência."""
        assunto = (
            f"[DJe Monitor] Publicação encontrada - {tribunal} "
            f"({data_publicacao})"
        )

        corpo_html = self._formatar_html_ocorrencia(
            cpf, nome, tribunal, data_publicacao, caderno, pagina, contexto
        )

        return self._enviar_email(assunto, corpo_html)

    def enviar_resumo_diario(
        self, total_diarios: int, total_ocorrencias: int, detalhes: list[dict]
    ) -> bool:
        """Envia resumo diário por email."""
        assunto = (
            f"[DJe Monitor] Resumo diário - "
            f"{total_ocorrencias} ocorrência(s)"
        )

        corpo_html = self._formatar_html_resumo(
            total_diarios, total_ocorrencias, detalhes
        )

        return self._enviar_email(assunto, corpo_html)

    def testar_conexao(self) -> bool:
        """Testa conexão com o servidor SMTP."""
        try:
            server = self._conectar_smtp()
            server.quit()
            logger.info(f"Conexão SMTP OK: {self.smtp_host}:{self.smtp_port}")
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar SMTP: {e}")
            return False

    def _enviar_email(self, assunto: str, corpo_html: str) -> bool:
        """Envia email via SMTP."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = assunto
            msg["From"] = self.smtp_user
            msg["To"] = ", ".join(self.destinatarios)

            # Versão texto simples
            texto_simples = corpo_html.replace("<br>", "\n")
            for tag in [
                "<b>", "</b>", "<i>", "</i>", "<h2>", "</h2>",
                "<h3>", "</h3>", "<p>", "</p>", "<ul>", "</ul>",
                "<li>", "</li>", "<hr>",
            ]:
                texto_simples = texto_simples.replace(tag, "")

            msg.attach(MIMEText(texto_simples, "plain", "utf-8"))
            msg.attach(MIMEText(corpo_html, "html", "utf-8"))

            server = self._conectar_smtp()
            server.sendmail(
                self.smtp_user, self.destinatarios, msg.as_string()
            )
            server.quit()

            logger.info(
                f"Email enviado para {len(self.destinatarios)} destinatário(s)"
            )
            return True

        except Exception as e:
            logger.error(f"Erro ao enviar email: {e}")
            return False

    def _conectar_smtp(self) -> smtplib.SMTP:
        """Estabelece conexão com servidor SMTP."""
        if self.smtp_port == 465:
            server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
        else:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()

        server.login(self.smtp_user, self.smtp_password)
        return server

    def _formatar_html_ocorrencia(
        self,
        cpf: str,
        nome: str,
        tribunal: str,
        data_publicacao: str,
        caderno: str,
        pagina: int | None,
        contexto: str,
    ) -> str:
        """Formata email HTML para ocorrência."""
        pagina_info = f"Página {pagina}" if pagina else "N/A"
        contexto_escaped = (
            contexto[:1000]
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1a5276;">Publicação encontrada no DJe</h2>

            <table style="border-collapse: collapse; width: 100%;">
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; background: #f5f5f5;">
                        <b>CPF</b>
                    </td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{cpf}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; background: #f5f5f5;">
                        <b>Nome</b>
                    </td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{nome or 'N/A'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; background: #f5f5f5;">
                        <b>Tribunal</b>
                    </td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{tribunal}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; background: #f5f5f5;">
                        <b>Data</b>
                    </td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{data_publicacao}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; background: #f5f5f5;">
                        <b>Caderno</b>
                    </td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{caderno}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; background: #f5f5f5;">
                        <b>Local</b>
                    </td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{pagina_info}</td>
                </tr>
            </table>

            <h3 style="color: #1a5276; margin-top: 20px;">Trecho da publicação:</h3>
            <div style="background: #f9f9f9; padding: 15px; border-left: 4px solid #1a5276;
                        font-size: 13px; white-space: pre-wrap; word-wrap: break-word;">
{contexto_escaped}
            </div>

            <hr style="margin-top: 30px;">
            <p style="color: #888; font-size: 11px;">
                DJe Monitor - Sistema automatizado de monitoramento de publicações.
            </p>
        </body>
        </html>
        """

    def _formatar_html_resumo(
        self, total_diarios: int, total_ocorrencias: int, detalhes: list[dict]
    ) -> str:
        """Formata email HTML para resumo diário."""
        linhas_detalhes = ""
        for d in detalhes[:20]:
            linhas_detalhes += f"""
                <tr>
                    <td style="padding: 6px; border: 1px solid #ddd;">{d.get('cpf', 'N/A')}</td>
                    <td style="padding: 6px; border: 1px solid #ddd;">{d.get('tribunal', 'N/A')}</td>
                    <td style="padding: 6px; border: 1px solid #ddd;">{d.get('data_publicacao', 'N/A')}</td>
                    <td style="padding: 6px; border: 1px solid #ddd;">{d.get('caderno', 'N/A')}</td>
                </tr>
            """

        status = (
            "Nenhuma ocorrência encontrada."
            if total_ocorrencias == 0
            else f"{total_ocorrencias} ocorrência(s) encontrada(s)."
        )

        tabela_detalhes = ""
        if detalhes:
            tabela_detalhes = f"""
            <h3>Detalhes das Ocorrências</h3>
            <table style="border-collapse: collapse; width: 100%;">
                <tr style="background: #1a5276; color: white;">
                    <th style="padding: 8px;">CPF</th>
                    <th style="padding: 8px;">Tribunal</th>
                    <th style="padding: 8px;">Data</th>
                    <th style="padding: 8px;">Caderno</th>
                </tr>
                {linhas_detalhes}
            </table>
            """

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1a5276;">Resumo do Monitoramento DJe</h2>

            <p><b>Diários processados:</b> {total_diarios}</p>
            <p><b>Ocorrências encontradas:</b> {total_ocorrencias}</p>
            <p><b>Status:</b> {status}</p>

            {tabela_detalhes}

            <hr style="margin-top: 30px;">
            <p style="color: #888; font-size: 11px;">
                DJe Monitor - Sistema automatizado de monitoramento de publicações.
            </p>
        </body>
        </html>
        """
