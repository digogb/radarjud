"""
Configurações do DJE Monitor.

Carrega configurações de variáveis de ambiente ou arquivo .env.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    # Tribunal principal para monitoramento
    tribunal: str = os.getenv("DJE_TRIBUNAL", "TJCE")

    # CPFs a monitorar (separados por vírgula na env var)
    cpfs_monitorados: list[str] = field(default_factory=list)

    # Fontes de dados
    usar_djen: bool = os.getenv("DJE_USAR_DJEN", "true").lower() == "true"
    usar_esaj: bool = os.getenv("DJE_USAR_ESAJ", "true").lower() == "true"

    # Diretórios
    base_dir: Path = Path(os.getenv("DJE_BASE_DIR", Path(__file__).parent.parent))
    data_dir: Path = field(init=False)
    pdf_dir: Path = field(init=False)

    # Database (obrigatório — PostgreSQL)
    database_url: str = os.getenv("DJE_DATABASE_URL", "")

    # Scheduler
    modo_scheduler: bool = os.getenv("DJE_MODO_SCHEDULER", "false").lower() == "true"
    hora_execucao: int = int(os.getenv("DJE_HORA_EXECUCAO", "7"))

    # Scraping
    request_timeout: int = int(os.getenv("DJE_REQUEST_TIMEOUT", "60"))
    delay_entre_requisicoes: float = float(os.getenv("DJE_DELAY_REQUISICOES", "1.5"))
    dias_retroativos: int = int(os.getenv("DJE_DIAS_RETROATIVOS", "3"))
    max_retries: int = int(os.getenv("DJE_MAX_RETRIES", "3"))

    # Notificações - Telegram
    telegram_bot_token: str = os.getenv("DJE_TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("DJE_TELEGRAM_CHAT_ID", "")

    # Notificações - Email
    smtp_host: str = os.getenv("DJE_SMTP_HOST", "")
    smtp_port: int = int(os.getenv("DJE_SMTP_PORT", "587"))
    smtp_user: str = os.getenv("DJE_SMTP_USER", "")
    smtp_password: str = os.getenv("DJE_SMTP_PASSWORD", "")
    email_destinatarios: list[str] = field(default_factory=list)

    # OCR
    ocr_lang: str = os.getenv("DJE_OCR_LANG", "por")
    ocr_dpi: int = int(os.getenv("DJE_OCR_DPI", "200"))

    # Matcher
    contexto_chars: int = int(os.getenv("DJE_CONTEXTO_CHARS", "500"))

    # Monitor de Pessoas
    monitor_habilitado: bool = os.getenv("DJE_MONITOR_HABILITADO", "true").lower() == "true"
    monitor_interval_minutes: int = int(os.getenv("DJE_MONITOR_INTERVAL_MINUTES", "30"))
    monitor_max_paginas: int = int(os.getenv("DJE_MONITOR_MAX_PAGINAS", "10"))

    # Redis / Task queue
    redis_url: str = os.getenv("DJE_REDIS_URL", "redis://localhost:6379/0")
    worker_threads: int = int(os.getenv("DJE_WORKER_THREADS", "8"))
    rate_limit_per_second: float = float(os.getenv("DJE_RATE_LIMIT_PER_SEC", "2.0"))

    def __post_init__(self):
        self.base_dir = Path(self.base_dir)
        self.data_dir = self.base_dir / "data"
        self.pdf_dir = self.data_dir / "pdfs"
        self.pdf_dir.mkdir(parents=True, exist_ok=True)

        if not self.database_url:
            raise ValueError(
                "DJE_DATABASE_URL não configurado. "
                "Defina a variável de ambiente com a URL do PostgreSQL, ex: "
                "postgresql://user:pass@localhost:5432/djedb"
            )

        # Carregar CPFs de env var se não fornecidos
        if not self.cpfs_monitorados:
            cpfs_env = os.getenv("DJE_CPFS_MONITORADOS", "")
            if cpfs_env:
                self.cpfs_monitorados = [
                    cpf.strip() for cpf in cpfs_env.split(",") if cpf.strip()
                ]

        # Carregar emails de env var se não fornecidos
        if not self.email_destinatarios:
            emails_env = os.getenv("DJE_EMAIL_DESTINATARIOS", "")
            if emails_env:
                self.email_destinatarios = [
                    e.strip() for e in emails_env.split(",") if e.strip()
                ]

    @property
    def telegram_habilitado(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    @property
    def email_habilitado(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.email_destinatarios)
