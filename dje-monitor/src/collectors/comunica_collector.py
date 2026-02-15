"""
Coletor para comunica.pje.jus.br usando Selenium.

Este coletor acessa a aplicação web (SPA) do Comunica PJe
e realiza buscas por nome/CPF diretamente, extraindo os trechos
de publicações relevantes.
"""

import logging
import time
from datetime import date
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)


class ComunicaCollector:
    """
    Coletor para buscar publicações no Comunica PJe (comunica.pje.jus.br).

    Usa Selenium para acessar a aplicação Angular e realizar buscas
    por nome/CPF nas publicações de todos os tribunais.
    """

    BASE_URL = "https://comunica.pje.jus.br"

    def __init__(self, headless: bool = True, timeout: int = 30):
        """
        Inicializa o coletor com Selenium.

        Args:
            headless: Se True, executa navegador sem interface gráfica
            timeout: Timeout em segundos para esperar elementos
        """
        self.headless = headless
        self.timeout = timeout
        self.driver = None

    def __enter__(self):
        """Context manager para inicializar o driver."""
        self._init_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager para fechar o driver."""
        self.close()

    def _init_driver(self):
        """Inicializa o webdriver do Chrome."""
        if self.driver:
            return

        options = Options()
        if self.headless:
            options.add_argument("--headless=new")

        # Opções essenciais para rodar em container
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-setuid-sandbox")
        options.add_argument("--single-process")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")
        options.add_argument(
            "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Preferências adicionais
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        options.add_experimental_option("useAutomationExtension", False)

        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(self.timeout)
            logger.info("WebDriver iniciado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao inicializar WebDriver: {e}")
            raise

    def close(self):
        """Fecha o navegador."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver fechado")
            except Exception as e:
                logger.warning(f"Erro ao fechar WebDriver: {e}")
            finally:
                self.driver = None

    def buscar_por_nome(
        self,
        nome: str,
        data_inicio: date,
        data_fim: date,
        tribunal: Optional[str] = None,
    ) -> list[dict]:
        """
        Busca publicações por nome de parte.

        Args:
            nome: Nome da parte a buscar
            data_inicio: Data inicial do período
            data_fim: Data final do período
            tribunal: Sigla do tribunal (opcional, busca em todos se None)

        Returns:
            Lista de dicionários com resultados encontrados
        """
        logger.info(
            f"Buscando '{nome}' no Comunica PJe "
            f"({data_inicio} a {data_fim})"
        )

        if not self.driver:
            self._init_driver()

        try:
            # Acessar página de consulta
            url = f"{self.BASE_URL}/consulta"
            self.driver.get(url)

            # Aguardar carregamento da aplicação Angular
            wait = WebDriverWait(self.driver, self.timeout)

            # Aguardar formulário de busca carregar
            time.sleep(3)  # Tempo para Angular inicializar

            # Preencher campos de busca
            self._preencher_formulario(
                nome, data_inicio, data_fim, tribunal, wait
            )

            # Submeter busca
            self._submeter_busca(wait)

            # Aguardar resultados
            time.sleep(2)

            # Extrair resultados
            resultados = self._extrair_resultados()

            logger.info(f"Encontrados {len(resultados)} resultados")
            return resultados

        except Exception as e:
            logger.error(f"Erro ao buscar no Comunica PJe: {e}")
            # Salvar screenshot para debug
            if self.driver:
                try:
                    self.driver.save_screenshot("/tmp/comunica_error.png")
                    logger.info("Screenshot salvo em /tmp/comunica_error.png")
                except Exception:
                    pass
            return []

    def buscar_por_cpf(
        self,
        cpf: str,
        data_inicio: date,
        data_fim: date,
        tribunal: Optional[str] = None,
    ) -> list[dict]:
        """
        Busca publicações por CPF.

        Args:
            cpf: CPF a buscar (apenas números)
            data_inicio: Data inicial do período
            data_fim: Data final do período
            tribunal: Sigla do tribunal (opcional)

        Returns:
            Lista de dicionários com resultados encontrados
        """
        # CPF pode ser buscado como nome de parte
        cpf_formatado = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
        return self.buscar_por_nome(
            cpf_formatado, data_inicio, data_fim, tribunal
        )

    def _preencher_formulario(
        self,
        nome: str,
        data_inicio: date,
        data_fim: date,
        tribunal: Optional[str],
        wait: WebDriverWait,
    ):
        """Preenche o formulário de busca."""
        try:
            # Campo de nome/parte
            # (seletores podem variar, tentar múltiplos)
            seletores_nome = [
                "input[name='nomeParte']",
                "input[placeholder*='nome']",
                "input[id*='nome']",
                "#nomeParte",
            ]

            for seletor in seletores_nome:
                try:
                    campo_nome = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, seletor))
                    )
                    campo_nome.clear()
                    campo_nome.send_keys(nome)
                    logger.debug(f"Campo nome preenchido com seletor: {seletor}")
                    break
                except Exception:
                    continue

            # Data início
            seletores_data_inicio = [
                "input[name='dataDisponibilizacaoInicio']",
                "input[id*='dataInicio']",
            ]

            for seletor in seletores_data_inicio:
                try:
                    campo_data_inicio = self.driver.find_element(
                        By.CSS_SELECTOR, seletor
                    )
                    campo_data_inicio.clear()
                    campo_data_inicio.send_keys(data_inicio.strftime("%Y-%m-%d"))
                    logger.debug("Data início preenchida")
                    break
                except Exception:
                    continue

            # Data fim
            seletores_data_fim = [
                "input[name='dataDisponibilizacaoFim']",
                "input[id*='dataFim']",
            ]

            for seletor in seletores_data_fim:
                try:
                    campo_data_fim = self.driver.find_element(
                        By.CSS_SELECTOR, seletor
                    )
                    campo_data_fim.clear()
                    campo_data_fim.send_keys(data_fim.strftime("%Y-%m-%d"))
                    logger.debug("Data fim preenchida")
                    break
                except Exception:
                    continue

            # Tribunal (se especificado)
            if tribunal:
                try:
                    campo_tribunal = self.driver.find_element(
                        By.CSS_SELECTOR, "select[name='siglaTribunal']"
                    )
                    campo_tribunal.send_keys(tribunal)
                    logger.debug(f"Tribunal {tribunal} selecionado")
                except Exception as e:
                    logger.debug(f"Campo tribunal não encontrado: {e}")

        except Exception as e:
            logger.error(f"Erro ao preencher formulário: {e}")
            raise

    def _submeter_busca(self, wait: WebDriverWait):
        """Submete o formulário de busca."""
        try:
            # Tentar encontrar botão de busca
            seletores_botao = [
                "button[type='submit']",
                "button:contains('Pesquisar')",
                "button:contains('Buscar')",
                ".btn-primary",
            ]

            for seletor in seletores_botao:
                try:
                    botao = wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, seletor))
                    )
                    botao.click()
                    logger.debug("Busca submetida")
                    return
                except Exception:
                    continue

            # Se não encontrou botão, tentar submit do form
            form = self.driver.find_element(By.TAG_NAME, "form")
            form.submit()
            logger.debug("Formulário submetido")

        except Exception as e:
            logger.error(f"Erro ao submeter busca: {e}")
            raise

    def _extrair_resultados(self) -> list[dict]:
        """Extrai resultados da página."""
        resultados = []

        try:
            # Aguardar resultados aparecerem
            time.sleep(2)

            # Tentar múltiplos seletores para resultados
            seletores_resultado = [
                ".resultado",
                ".item-resultado",
                ".card-resultado",
                "tr[class*='resultado']",
                ".list-group-item",
            ]

            elementos = []
            for seletor in seletores_resultado:
                try:
                    elementos = self.driver.find_elements(By.CSS_SELECTOR, seletor)
                    if elementos:
                        logger.debug(
                            f"Encontrados {len(elementos)} resultados "
                            f"com seletor: {seletor}"
                        )
                        break
                except Exception:
                    continue

            if not elementos:
                logger.warning("Nenhum resultado encontrado na página")
                return resultados

            # Extrair dados de cada resultado
            for elem in elementos:
                try:
                    texto = elem.text
                    if not texto or len(texto) < 20:
                        continue

                    # Tentar extrair dados estruturados
                    resultado = {
                        "texto": texto[:2000],  # Limitar tamanho
                        "html": elem.get_attribute("innerHTML")[:1000],
                    }

                    # Tentar extrair link
                    try:
                        link = elem.find_element(By.TAG_NAME, "a")
                        resultado["url"] = link.get_attribute("href")
                    except Exception:
                        resultado["url"] = ""

                    # Tentar extrair tribunal
                    try:
                        tribunal_elem = elem.find_element(
                            By.CSS_SELECTOR, "[class*='tribunal']"
                        )
                        resultado["tribunal"] = tribunal_elem.text
                    except Exception:
                        resultado["tribunal"] = ""

                    # Tentar extrair data
                    try:
                        data_elem = elem.find_element(
                            By.CSS_SELECTOR, "[class*='data']"
                        )
                        resultado["data"] = data_elem.text
                    except Exception:
                        resultado["data"] = ""

                    resultados.append(resultado)

                except Exception as e:
                    logger.debug(f"Erro ao extrair resultado: {e}")
                    continue

        except Exception as e:
            logger.error(f"Erro ao extrair resultados: {e}")

        return resultados
