"""
DJE Monitor - Entry point.

Sistema automatizado para buscar publicações no Diário da Justiça
Eletrônico (DJe/DJEN), identificando menções a CPFs monitorados.
"""

import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from collectors.base import DiarioItem
from collectors.djen_collector import DJENCollector
from collectors.esaj_collector import ESAJCollector
from config import Config
from extractors.ocr_extractor import OCRExtractor
from extractors.pdf_extractor import PDFExtractor
from matchers.cpf_matcher import CPFMatcher
from notifiers.email_notifier import EmailNotifier
from notifiers.telegram import MensagemOcorrencia, TelegramNotifier
from storage.models import Base
from storage.repository import DiarioRepository

console = Console()


def setup_logging(verbose: bool = False):
    """Configura logging com Rich handler."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )


logger = logging.getLogger(__name__)


class DJEMonitor:
    """Orquestrador principal do sistema de monitoramento."""

    def __init__(self, config: Config):
        self.config = config
        self.repository = DiarioRepository(config.database_url)
        self.pdf_extractor = PDFExtractor()
        self.ocr_extractor = OCRExtractor(
            lang=config.ocr_lang, dpi=config.ocr_dpi
        )
        self.cpf_matcher = CPFMatcher(contexto_chars=config.contexto_chars)
        self.collectors = self._init_collectors()
        self.notifiers = self._init_notifiers()

    def _init_collectors(self) -> list:
        """Inicializa coletores baseado na configuração."""
        collectors = []
        kwargs = {
            "timeout": self.config.request_timeout,
            "delay": self.config.delay_entre_requisicoes,
            "max_retries": self.config.max_retries,
        }

        if self.config.usar_djen:
            try:
                collectors.append(
                    DJENCollector(self.config.tribunal, **kwargs)
                )
                logger.info(f"Coletor DJEN inicializado para {self.config.tribunal}")
            except Exception as e:
                logger.error(f"Erro ao inicializar coletor DJEN: {e}")

        if self.config.usar_esaj:
            try:
                collectors.append(
                    ESAJCollector(self.config.tribunal, **kwargs)
                )
                logger.info(f"Coletor e-SAJ inicializado para {self.config.tribunal}")
            except Exception as e:
                logger.warning(f"Coletor e-SAJ não disponível: {e}")

        return collectors

    def _init_notifiers(self) -> list:
        """Inicializa notificadores baseado na configuração."""
        notifiers = []

        if self.config.telegram_habilitado:
            notifiers.append(
                TelegramNotifier(
                    self.config.telegram_bot_token,
                    self.config.telegram_chat_id,
                )
            )
            logger.info("Notificador Telegram inicializado")

        if self.config.email_habilitado:
            notifiers.append(
                EmailNotifier(
                    self.config.smtp_host,
                    self.config.smtp_port,
                    self.config.smtp_user,
                    self.config.smtp_password,
                    self.config.email_destinatarios,
                )
            )
            logger.info("Notificador Email inicializado")

        return notifiers

    def executar(self):
        """Executa verificação para os últimos N dias."""
        logger.info(
            f"Iniciando monitoramento - {self.config.dias_retroativos} dias "
            f"retroativos para {self.config.tribunal}"
        )

        hoje = date.today()
        total_diarios = 0
        total_ocorrencias = 0
        detalhes_ocorrencias = []

        for i in range(self.config.dias_retroativos):
            data = hoje - timedelta(days=i)
            diarios, ocorrencias = self.processar_dia(data)
            total_diarios += diarios
            total_ocorrencias += ocorrencias

        # Enviar resumo
        if self.notifiers and total_diarios > 0:
            self._enviar_resumo(
                total_diarios, total_ocorrencias, detalhes_ocorrencias
            )

        logger.info(
            f"Monitoramento concluído: {total_diarios} diários, "
            f"{total_ocorrencias} ocorrências"
        )

    def processar_dia(self, data: date, nome_busca: str = None) -> tuple[int, int]:
        """
        Processa publicações de um dia (busca por diário ou nome).

        Args:
            data: Data da publicação/disponibilização.
            nome_busca: Se fornecido, faz busca direta por nome na API (DJEN).

        Returns:
            Tupla (diários processados, ocorrências encontradas).
        """
        logger.info(f"Processando publicações de {data}")
        diarios_processados = 0
        ocorrencias_encontradas = 0

        for collector in self.collectors:
            collector_name = type(collector).__name__
            try:
                # ESTRATÉGIA 1: Busca Direta por Nome (API DJEN)
                if nome_busca and isinstance(collector, DJENCollector):
                    logger.info(f"Busca direta por nome '{nome_busca}' no {collector_name}")
                    resultados = collector.buscar_por_nome(nome_busca, data, data)
                    
                    if resultados:
                         console.print(f"\n[bold green]Encontrados {len(resultados)} resultados para '{nome_busca}':[/bold green]")
                         table = Table(show_header=True, header_style="bold magenta")
                         table.add_column("Processo")
                         table.add_column("Data")
                         table.add_column("Órgão")
                         table.add_column("Conteúdo (Resumo)")
                         
                         for res in resultados:
                             # Salvar/Notificar aqui se necessário
                             processo = res.get("processo", "N/A")
                             dt = res.get("data_disponibilizacao", str(data))
                             orgao = res.get("orgao", "N/A")
                             texto = res.get("texto", "")[:100].replace("\n", " ") + "..."
                             
                             table.add_row(processo, dt, orgao, texto)
                             
                             ocorrencias_encontradas += 1
                             
                         console.print(table)
                         console.print("\n")
                    else:
                        logger.info(f"Nenhum resultado para '{nome_busca}' nesta data.")

                    continue # Pula listagem de edições se for busca por nome

                # ESTRATÉGIA 2: Baixar Diários (Legado/e-SAJ)
                edicoes = collector.listar_edicoes(data)
                logger.info(
                    f"{collector_name}: {len(edicoes)} edições para {data}"
                )

                for edicao in edicoes:
                    ocs = self._processar_edicao(edicao, collector)
                    diarios_processados += 1
                    ocorrencias_encontradas += ocs

            except Exception as e:
                logger.error(f"Erro no {collector_name}: {e}", exc_info=True)

        return diarios_processados, ocorrencias_encontradas

    def _processar_edicao(self, edicao: DiarioItem, collector) -> int:
        """
        Processa uma edição específica do diário.

        Returns:
            Número de ocorrências encontradas.
        """
        fonte = edicao.metadata.get("fonte", type(collector).__name__)

        # 1. Verificar se já processado
        if self.repository.diario_ja_processado(
            edicao.tribunal,
            edicao.data_publicacao,
            edicao.caderno,
            fonte,
        ):
            logger.debug(f"Edição já processada: {edicao}")
            return 0

        # 2. Baixar PDF
        pdf_filename = (
            f"{edicao.tribunal}_{edicao.data_publicacao}_"
            f"caderno{edicao.caderno}_{fonte}.pdf"
        )
        pdf_path = self.config.pdf_dir / pdf_filename

        downloaded = collector.baixar_pdf(edicao.url_pdf, pdf_path)
        if not downloaded:
            logger.warning(f"Falha ao baixar: {edicao.url_pdf}")
            return 0

        hash_arquivo = collector.calcular_hash(pdf_path)

        # 3. Registrar diário
        diario = self.repository.registrar_diario(
            tribunal=edicao.tribunal,
            fonte=fonte,
            data_publicacao=edicao.data_publicacao,
            caderno=edicao.caderno,
            caderno_nome=edicao.caderno_nome,
            edicao=edicao.edicao,
            url_original=edicao.url_pdf,
            caminho_pdf=str(pdf_path),
            hash_arquivo=hash_arquivo,
            num_paginas=edicao.num_paginas,
        )

        # 4. Extrair texto
        texto_paginas = self._extrair_texto(pdf_path)
        if not texto_paginas:
            logger.warning(f"Nenhum texto extraído de {pdf_path}")
            return 0

        self.repository.marcar_texto_extraido(diario.id)

        # 5. Buscar CPFs monitorados
        cpfs = self.repository.listar_cpfs_ativos()
        total_ocorrencias = 0

        for cpf_obj in cpfs:
            matches = self.cpf_matcher.buscar_cpf_por_pagina(
                texto_paginas, cpf_obj.cpf
            )

            for match in matches:
                self.repository.registrar_ocorrencia(
                    cpf_id=cpf_obj.id,
                    diario_id=diario.id,
                    pagina=match.pagina,
                    posicao=match.posicao_inicio,
                    contexto=match.contexto,
                )
                total_ocorrencias += 1

                # Notificar imediatamente
                self._notificar_ocorrencia(cpf_obj, edicao, match)

                logger.info(
                    f"Ocorrência encontrada: CPF {cpf_obj.cpf} em "
                    f"{edicao.tribunal} {edicao.data_publicacao} "
                    f"caderno {edicao.caderno} página {match.pagina}"
                )

        # 6. Marcar como processado
        self.repository.marcar_processado(diario.id)

        return total_ocorrencias

    def executar_busca_periodo(self, nome: str, data_inicio: date, data_fim: date):
        """Executa busca por nome em um período (apenas DJEN)."""
        logger.info(f"Buscando '{nome}' de {data_inicio} a {data_fim}")
        
        for collector in self.collectors:
            if isinstance(collector, DJENCollector):
                try:
                    resultados = collector.buscar_por_nome(nome, data_inicio, data_fim)
                    if resultados:
                         console.print(f"\n[bold green]Encontrados {len(resultados)} resultados para '{nome}' ({data_inicio} a {data_fim}):[/bold green]")
                         table = Table(show_header=True, header_style="bold magenta")
                         table.add_column("Processo")
                         table.add_column("Data")
                         table.add_column("Órgão")
                         table.add_column("Conteúdo (Resumo)")
                         
                         for res in resultados:
                             processo = res.get("processo", "N/A")
                             dt = res.get("data_disponibilizacao", "")
                             orgao = res.get("orgao", "N/A")
                             texto = res.get("texto", "")[:100].replace("\n", " ") + "..."
                             
                             table.add_row(processo, dt, orgao, texto)
                         
                         console.print(table)
                    else:
                        console.print(f"[yellow]Nenhum resultado encontrado para '{nome}' no período.[/yellow]")
                        
                except Exception as e:
                    logger.error(f"Erro na busca por nome: {e}")

    def _extrair_texto(self, pdf_path: Path) -> list[tuple[int, str]]:
        """
        Extrai texto do PDF, usando OCR se necessário.

        Returns:
            Lista de (num_pagina, texto).
        """
        paginas = self.pdf_extractor.extrair_por_pagina(pdf_path)

        if not paginas:
            return []

        # Verificar se o PDF é escaneado
        texto_total = sum(len(t) for _, t in paginas)
        num_paginas = len(paginas)

        if num_paginas > 0 and (texto_total / num_paginas) < 100:
            if self.ocr_extractor.detectar_se_escaneado(pdf_path):
                logger.info(f"PDF escaneado detectado, usando OCR: {pdf_path}")
                paginas = self.ocr_extractor.pdf_para_texto_por_pagina(pdf_path)

        return paginas

    def _notificar_ocorrencia(self, cpf_obj, edicao: DiarioItem, match):
        """Envia notificações para uma ocorrência encontrada."""
        for notifier in self.notifiers:
            try:
                if isinstance(notifier, TelegramNotifier):
                    msg = MensagemOcorrencia(
                        cpf=self.cpf_matcher.formatar_cpf(cpf_obj.cpf),
                        nome=cpf_obj.nome or "",
                        tribunal=edicao.tribunal,
                        data_publicacao=str(edicao.data_publicacao),
                        caderno=edicao.caderno_nome or edicao.caderno,
                        pagina=match.pagina,
                        contexto=match.contexto,
                    )
                    notifier.enviar_ocorrencia(msg)

                elif isinstance(notifier, EmailNotifier):
                    notifier.enviar_ocorrencia(
                        cpf=self.cpf_matcher.formatar_cpf(cpf_obj.cpf),
                        nome=cpf_obj.nome or "",
                        tribunal=edicao.tribunal,
                        data_publicacao=str(edicao.data_publicacao),
                        caderno=edicao.caderno_nome or edicao.caderno,
                        pagina=match.pagina,
                        contexto=match.contexto,
                    )
            except Exception as e:
                logger.error(
                    f"Erro ao notificar via {type(notifier).__name__}: {e}"
                )

    def _enviar_resumo(
        self, total_diarios: int, total_ocorrencias: int, detalhes: list[dict]
    ):
        """Envia resumo para todos os notificadores."""
        for notifier in self.notifiers:
            try:
                notifier.enviar_resumo_diario(
                    total_diarios, total_ocorrencias, detalhes
                )
            except Exception as e:
                logger.error(
                    f"Erro ao enviar resumo via {type(notifier).__name__}: {e}"
                )


def cmd_executar(args, config: Config):
    """Comando: executar monitoramento."""
    monitor = DJEMonitor(config)

    if args.data:
        data = date.fromisoformat(args.data)
        # Se nome fornecido, busca só nesse dia
        if args.nome:
             monitor.executar_busca_periodo(args.nome, data, data)
        else:
             monitor.processar_dia(data)
    else:
        # Se tiver nome, processar período completo de uma vez
        if args.nome:
             hoje = date.today()
             data_inicio = hoje - timedelta(days=config.dias_retroativos)
             monitor.executar_busca_periodo(args.nome, data_inicio, hoje)
        else:
            monitor.executar()


def cmd_adicionar_cpf(args, config: Config):
    """Comando: adicionar CPF para monitoramento."""
    repo = DiarioRepository(config.database_url)
    cpf = CPFMatcher.normalizar_cpf(args.cpf)

    if not CPFMatcher.validar_cpf(cpf):
        console.print(f"[red]CPF inválido: {args.cpf}[/red]")
        sys.exit(1)

    repo.adicionar_cpf(cpf, nome=args.nome or "")
    cpf_fmt = CPFMatcher.formatar_cpf(cpf)
    console.print(f"[green]CPF {cpf_fmt} adicionado para monitoramento.[/green]")


def cmd_remover_cpf(args, config: Config):
    """Comando: remover CPF do monitoramento."""
    repo = DiarioRepository(config.database_url)
    cpf = CPFMatcher.normalizar_cpf(args.cpf)
    if repo.remover_cpf(cpf):
        console.print(f"[yellow]CPF {args.cpf} removido do monitoramento.[/yellow]")
    else:
        console.print(f"[red]CPF {args.cpf} não encontrado.[/red]")


def cmd_listar_cpfs(args, config: Config):
    """Comando: listar CPFs monitorados."""
    repo = DiarioRepository(config.database_url)
    cpfs = repo.listar_cpfs_ativos()

    if not cpfs:
        console.print("[yellow]Nenhum CPF monitorado.[/yellow]")
        return

    table = Table(title="CPFs Monitorados")
    table.add_column("ID", style="dim")
    table.add_column("CPF", style="cyan")
    table.add_column("Nome")
    table.add_column("Desde")

    for cpf in cpfs:
        table.add_row(
            str(cpf.id),
            CPFMatcher.formatar_cpf(cpf.cpf),
            cpf.nome or "-",
            cpf.criado_em.strftime("%d/%m/%Y") if cpf.criado_em else "-",
        )

    console.print(table)


def cmd_ocorrencias(args, config: Config):
    """Comando: listar ocorrências para um CPF."""
    repo = DiarioRepository(config.database_url)
    cpf = CPFMatcher.normalizar_cpf(args.cpf)
    ocorrencias = repo.listar_ocorrencias_por_cpf(cpf, limite=args.limite)

    if not ocorrencias:
        console.print(f"[yellow]Nenhuma ocorrência para CPF {args.cpf}.[/yellow]")
        return

    table = Table(title=f"Ocorrências - CPF {CPFMatcher.formatar_cpf(cpf)}")
    table.add_column("Data", style="cyan")
    table.add_column("Tribunal")
    table.add_column("Caderno")
    table.add_column("Página")
    table.add_column("Notificado")

    for oc in ocorrencias:
        table.add_row(
            str(oc["data_publicacao"]),
            oc["tribunal"],
            oc["caderno"],
            str(oc["pagina"] or "-"),
            "Sim" if oc["notificado"] else "Não",
        )

    console.print(table)

    if args.contexto and ocorrencias:
        console.print("\n[bold]Contexto da última ocorrência:[/bold]")
        console.print(ocorrencias[0].get("contexto", "N/A"))


def cmd_status(args, config: Config):
    """Comando: mostrar estatísticas do sistema."""
    repo = DiarioRepository(config.database_url)
    stats = repo.estatisticas()

    table = Table(title="Status do DJE Monitor")
    table.add_column("Métrica", style="cyan")
    table.add_column("Valor", style="green")

    table.add_row("CPFs monitorados", str(stats["cpfs_monitorados"]))
    table.add_row("Diários processados", str(stats["diarios_processados"]))
    table.add_row("Diários pendentes", str(stats["diarios_pendentes"]))
    table.add_row("Total de ocorrências", str(stats["total_ocorrencias"]))
    table.add_row(
        "Ocorrências não notificadas",
        str(stats["ocorrencias_nao_notificadas"]),
    )

    console.print(table)


def cmd_scheduler(args, config: Config):
    """Comando: iniciar scheduler para execução automática."""
    monitor = DJEMonitor(config)
    scheduler = BlockingScheduler()

    hora = config.hora_execucao
    scheduler.add_job(monitor.executar, "cron", hour=hora, minute=0)

    console.print(
        f"[green]Scheduler iniciado. Execução diária às {hora:02d}:00.[/green]"
    )
    console.print("Pressione Ctrl+C para parar.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        console.print("\n[yellow]Scheduler encerrado.[/yellow]")


def main():
    parser = argparse.ArgumentParser(
        description="DJE Monitor - Monitor de Publicações do Diário da Justiça Eletrônico",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Ativa modo verbose"
    )
    parser.add_argument(
        "--tribunal", default=None, help="Tribunal (ex: TJCE, TJSP)"
    )

    subparsers = parser.add_subparsers(dest="comando", help="Comandos disponíveis")

    p_exec = subparsers.add_parser("executar", help="Executar monitoramento")
    p_exec.add_argument("--data", help="Data específica (YYYY-MM-DD)")
    p_exec.add_argument(
        "--dias", type=int, help="Número de dias retroativos"
    )
    p_exec.add_argument("--nome", help="Nome da parte para buscar no DJEN (substitui busca por diário)")

    # Comando: adicionar-cpf
    p_add = subparsers.add_parser("adicionar-cpf", help="Adicionar CPF")
    p_add.add_argument("cpf", help="CPF a monitorar")
    p_add.add_argument("--nome", help="Nome da pessoa")

    # Comando: remover-cpf
    p_rem = subparsers.add_parser("remover-cpf", help="Remover CPF")
    p_rem.add_argument("cpf", help="CPF a remover")

    # Comando: listar-cpfs
    subparsers.add_parser("listar-cpfs", help="Listar CPFs monitorados")

    # Comando: ocorrencias
    p_oc = subparsers.add_parser("ocorrencias", help="Listar ocorrências")
    p_oc.add_argument("cpf", help="CPF para buscar ocorrências")
    p_oc.add_argument("--limite", type=int, default=50, help="Limite de resultados")
    p_oc.add_argument(
        "--contexto", action="store_true", help="Mostrar contexto"
    )

    # Comando: status
    subparsers.add_parser("status", help="Mostrar estatísticas")

    # Comando: scheduler
    subparsers.add_parser("scheduler", help="Iniciar scheduler")

    args = parser.parse_args()
    setup_logging(verbose=args.verbose)

    config = Config()
    if args.tribunal:
        config.tribunal = args.tribunal

    if hasattr(args, "dias") and args.dias:
        config.dias_retroativos = args.dias

    comandos = {
        "executar": cmd_executar,
        "adicionar-cpf": cmd_adicionar_cpf,
        "remover-cpf": cmd_remover_cpf,
        "listar-cpfs": cmd_listar_cpfs,
        "ocorrencias": cmd_ocorrencias,
        "status": cmd_status,
        "scheduler": cmd_scheduler,
    }

    if args.comando in comandos:
        comandos[args.comando](args, config)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
