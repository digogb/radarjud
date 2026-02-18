"""
Coletor para o DJEN - Diário de Justiça Eletrônico Nacional (CNJ).

Fonte: https://comunica.pje.jus.br/
Cobertura: Todos os tribunais que usam PJe.
"""

import logging
import re
from datetime import date
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseCollector, DiarioItem
from utils.data_normalizer import normalizar_nome

logger = logging.getLogger(__name__)


class DJENCollector(BaseCollector):
    """
    Coletor para o DJEN (comunica.pje.jus.br).

    O DJEN disponibiliza publicações de todos os tribunais que usam PJe.
    Possui interface de busca textual que permite buscar diretamente por CPF.
    """

    BASE_URL = "https://comunica.pje.jus.br"
    API_URL = "https://comunicaapi.pje.jus.br/api/v1/comunicacao"

    # Mapeamento de siglas para IDs de órgão no DJEN
    ORGAOS = {
        "TJCE": "TJCE",
        "TJSP": "TJSP",
        "TJRJ": "TJRJ",
        "TJMG": "TJMG",
        "TJRS": "TJRS",
        "TJPR": "TJPR",
        "TJSC": "TJSC",
        "TJBA": "TJBA",
        "TJPE": "TJPE",
        "TJGO": "TJGO",
        "TRF1": "TRF1",
        "TRF2": "TRF2",
        "TRF3": "TRF3",
        "TRF4": "TRF4",
        "TRF5": "TRF5",
        "TRT1": "TRT1",
        "TST": "TST",
        "STJ": "STJ",
    }

    def __init__(self, tribunal: str = "TJCE", **kwargs):
        super().__init__(tribunal=tribunal, **kwargs)
        self.orgao_id = self.ORGAOS.get(tribunal, tribunal)

    def listar_edicoes(self, data: date) -> list[DiarioItem]:
        """
        Lista edições do DJEN para o tribunal e data especificados.

        Faz scraping da página de consulta do DJEN para encontrar
        edições disponíveis.
        """
        logger.info(f"Listando edições DJEN para {self.tribunal} em {data}")
        items = []

        url = f"{self.BASE_URL}/consulta"
        params = {
            "orgao": self.orgao_id,
            "dataInicial": data.strftime("%Y-%m-%d"),
            "dataFinal": data.strftime("%Y-%m-%d"),
        }

        response = self._fazer_requisicao("GET", url, params=params)
        if not response:
            return items

        try:
            # O DJEN pode retornar JSON ou HTML dependendo do endpoint
            content_type = response.headers.get("content-type", "")

            if "application/json" in content_type:
                items = self._parse_json_response(response.json(), data)
            else:
                items = self._parse_html_response(response.text, data)
        except Exception as e:
            logger.error(f"Erro ao parsear resposta do DJEN: {e}")

        logger.info(f"Encontradas {len(items)} edições no DJEN")
        return items

    def buscar_por_termo(
        self, termo: str, data_inicio: date, data_fim: date
    ) -> list[dict]:
        """Implementação do método abstrato - Alias para buscar_por_nome."""
        return self.buscar_por_nome(termo, data_inicio, data_fim)

    def buscar_por_termo(
        self, termo: str, data_inicio: date, data_fim: date
    ) -> list[dict]:
        """Implementação do método abstrato - Alias para buscar_por_nome."""
        return self.buscar_por_nome(termo, data_inicio, data_fim)

    def buscar_por_nome(
        self, nome: str, data_inicio: date, data_fim: date, max_paginas: int = 50
    ) -> list[dict]:
        """
        Busca comunicações no DJEN pelo Nome da Parte ou Número do Processo.
        Retorna lista de resultados estruturados.
        """
        logger.info(
            f"Buscando '{nome}' no DJEN ({data_inicio} a {data_fim}) - Máx {max_paginas} págs"
        )
        resultados = []

        # Detecção simples de número de processo (CNJ ou apenas números longos)
        # Formato CNJ: 0000000-00.0000.0.00.0000 (20 digitos + masc)
        termo_limpo = re.sub(r"\D", "", nome)
        is_processo = (len(termo_limpo) >= 15 and ("-" in nome or len(termo_limpo) == 20))

        params = {
            "itensPorPagina": 100,
            "pagina": 1,
        }

        if is_processo:
            params["numeroProcesso"] = nome
            logger.info(f"Detectado busca por processo: {nome}")
        else:
            params["nomeParte"] = nome

        # Loop de paginação
        while True:
            logger.info(f"Buscando página {params['pagina']}...")
            try:
                response = self._fazer_requisicao(
                    "GET", self.API_URL, params=params, headers={"Accept": "application/json"}
                )
                
                if response and response.status_code == 200:
                    # Debug: verificar content type
                    ct = response.headers.get("content-type", "")
                    if "html" in ct:
                         raise ValueError("API retornou HTML")

                    data_resp = response.json()
                    
                    novos_items = []
                    if "items" in data_resp:
                        novos_items = self._parse_comunicacoes_json(data_resp["items"], nome, pular_filtro_destinatario=is_processo)
                    elif isinstance(data_resp, list):
                         novos_items = self._parse_comunicacoes_json(data_resp, nome, pular_filtro_destinatario=is_processo)
                    
                    if not novos_items:
                        break
                        
                    resultados.extend(novos_items)
                    
                    # Verificar se há mais páginas (baseado no total ou apenas se trouxe items)
                    total_count = data_resp.get("count", 0) if isinstance(data_resp, dict) else len(novos_items)
                    # Se trouxe menos que o limite, provavelmente acabou
                    if len(novos_items) < params["itensPorPagina"]:
                        break
                        
                    params["pagina"] += 1
                    
                    # Limite de segurança para não loopar infinito
                    if params["pagina"] > max_paginas:
                        logger.warning(f"Limite de {max_paginas} páginas atingido na busca por nome.")
                        break
                else:
                    logger.warning(f"Erro na requisição (Pag {params['pagina']}): Status {response.status_code if response else 'None'}")
                    # Se der erro 404 ou 500 na paginação, paramos
                    break
                    
            except Exception as e:
                logger.warning(f"Erro na API direta ({self.API_URL}): {e}")
                break
        
        return resultados




    def _parse_comunicacoes_json(self, items: list, termo: str, pular_filtro_destinatario: bool = False) -> list[dict]:
        """Parseia comunicações retornadas pela API JSON."""
        resultados = []
        # Normaliza o termo removendo acentos para comparação robusta
        termo_norm = normalizar_nome(termo)

        for item in items:
            try:
                # Verificar dados de destinatários
                destinatarios = item.get("destinatarios", [])

                # Se NÃO for busca por processo, filtrar pelo nome do destinatário
                # Usa normalizar_nome em ambos os lados para ignorar diferenças de acento
                # Ex: "JOAO" (planilha) casa com "JOÃO" (API)
                if not pular_filtro_destinatario:
                    encontrou_exato = False
                    for dest in destinatarios:
                        nome_dest = dest.get("nome", "")
                        if normalizar_nome(nome_dest) == termo_norm:
                            encontrou_exato = True
                            break

                    if not encontrou_exato:
                        continue

                # Obter texto bruto (pode vir como 'texto' ou 'conteudo')
                raw_texto = item.get("texto") or item.get("conteudo") or ""
                texto_conteudo = self._limpar_html(raw_texto)

                # Extrair dados ricos do JSON tentando múltiplas chaves
                processo = (
                    item.get("numeroprocessocommascara") or 
                    item.get("numeroProcesso") or 
                    item.get("numero_processo") or ""
                )
                
                data_disp = (
                    item.get("datadisponibilizacao") or 
                    item.get("dataDisponibilizacao") or 
                    item.get("data_disponibilizacao") or ""
                )
                
                orgao = item.get("nomeOrgao", "")

                # Fallback: Extrair do texto se não veio no JSON
                if not processo:
                    match_proc = re.search(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}", texto_conteudo)
                    if match_proc:
                        processo = match_proc.group(0)
                
                if not data_disp:
                    match_data = re.search(r"\d{2}/\d{2}/\d{4}", texto_conteudo)
                    if match_data:
                        data_disp = match_data.group(0)
                
                if not orgao:
                    # Tentar extrair sigla de tribunal ou vara do texto
                    orgao = item.get("siglaTribunal", self.tribunal)

                # Extração de polos baseada EXCLUSIVAMENTE nos dados estruturados da API
                polos = {"ativo": [], "passivo": [], "outros": []}
                
                # Iterar sobre todos os destinatários retornados
                todos_destinatarios = item.get("destinatarios", [])
                for dest in todos_destinatarios:
                    nome = dest.get("nome", "").strip()
                    if not nome: continue
                    
                    # Tentar identificar o polo pelos campos da API (polo, tipoParte, etc)
                    # O usuário confirmou: 'A' = Ativo, 'P' = Passivo
                    tipo_polo = str(dest.get("polo", "")).upper()
                    
                    if tipo_polo == "A" or "ATIVO" in tipo_polo or "AUTOR" in tipo_polo:
                        polos["ativo"].append(nome)
                    elif tipo_polo == "P" or "PASSIVO" in tipo_polo or "REU" in tipo_polo or "RÉU" in tipo_polo:
                        polos["passivo"].append(nome)
                    else:
                        # Se não tiver classificação, vai para lista genérica
                        polos["outros"].append(nome)

                res = {
                    "tribunal": item.get("siglaTribunal", self.tribunal),
                    "processo": processo,
                    "data_disponibilizacao": data_disp,
                    "orgao": orgao,
                    "tipo_comunicacao": item.get("tipoComunicacao", ""),
                    "texto": texto_conteudo,
                    "meio": item.get("meio", ""),
                    "link": item.get("link", ""),
                    "id": item.get("id", ""),
                    "termo_buscado": termo,
                    "fonte": "DJEN API",
                    # Dados extras para contexto
                    "partes": [d.get("nome", "") for d in destinatarios], # Legado (filtrado pela busca)
                    "polos": polos, # Estrutura completa
                    "raw_data": item 
                }
                
                # Se não tiver texto no item principal, tentar montar do HTML ou buscar link
                if not res["texto"] and res["id"]:
                     res["texto"] = f"Comunicação ID {res['id']} - Ver link: {res['link']}"

                resultados.append(res)
            except Exception as e:
                logger.error(f"Erro ao parsear item JSON: {e}")
                
        return resultados

    def _extrair_polos_do_texto(self, texto: str) -> dict:
        """
        Tenta extrair polos ativo e passivo do texto da publicação usando Regex.
        Retorna dict com listas de nomes.
        Refinado para evitar capturar o corpo do texto.
        """
        if not texto:
            return {"ativo": [], "passivo": [], "outros": []}
            
        polos = {"ativo": [], "passivo": [], "outros": []}
        texto_upper = texto.upper()
        
        # Regex patterns refinados
        # Pega até encontrar :, \n, ou ponto final (exceto abreviações comuns protejidas depois)
        # Limita a captura para evitar pegar o texto inteiro
        patterns = {
            "ativo": [
                r"(?:AUTOR|EXEQUENTE|REQUERENTE|IMPETRANTE|EMBARGANTE|SUSCITANTE|APELANTE|AGRAVANTE|RECORRENTE)[AEIS]*\s*[:]\s*([^:\n]{3,180})"
            ],
            "passivo": [
                r"(?:R[ÉE]U|EXECUTADO|REQUERIDO|IMPETRADO|EMBARGADO|SUSCITADO|APELADO|AGRAVADO|RECORRIDO)[AEIS]*\s*[:]\s*([^:\n]{3,180})"
            ],
            "outros": [
                r"(?:ADVOGAD[OA]|PATRONO)[S]*\s*[:]\s*([^:\n]{3,180})"
            ]
        }
        
        # Expressão para limpar o nome capturado
        def limpar_nome(raw_nome):
            # Remove marcadores de fim comuns que possam ter vindo
            # Pára em " - ", " Advogado", " Juiz", etc
            token_fim = re.split(r"\s-\s|ADVOGAD|R[ÉE]U|AUTOR|JUIZ|OAB|CPF|CNPJ|\.\s|;|(?:\s\w{2}\s)", raw_nome)
            nome = token_fim[0]
            return nome.strip().title()

        for tipo, lista_patterns in patterns.items():
            for pat in lista_patterns:
                matches = re.finditer(pat, texto_upper)
                for match in matches:
                    conteudo = match.group(1)
                    # Se tiver vírgula, pode ser lista de nomes
                    nomes_brutos = conteudo.split(',')
                    
                    for nb in nomes_brutos:
                        nome_limpo = limpar_nome(nb)
                        
                        # Critérios de Aceite:
                        # 1. Tamanho razoável (3 a 80 chars)
                        # 2. Não deve ser uma frase longa (contar palavras)
                        if 3 < len(nome_limpo) < 80:
                            # Se tiver mais de 10 palavras, provavelmente é lixo
                            if len(nome_limpo.split()) > 10:
                                continue
                                
                            # Filtrar "nomes" que são na verdade inícios de frases comuns
                            if nome_limpo.upper() in ["A", "O", "OS", "AS", "DE", "DA", "DO", "EM", "NA", "NO"]:
                                continue
                                
                            if nome_limpo not in polos[tipo]:
                                polos[tipo].append(nome_limpo)
                            
        return polos

    def _limpar_html(self, html_content: str) -> str:
        """Limpa tags HTML e retira apenas o texto legível."""
        if not html_content:
            return ""
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Remover scripts e estilos
            for script in soup(["script", "style", "header", "footer", "nav"]):
                script.decompose()

            # Quebrar linhas em tags de bloco para garantir separação
            for br in soup.find_all("br"):
                br.replace_with("\n")
            for tag in soup.find_all(["p", "div", "li", "tr"]):
                tag.insert_after("\n")

            text = soup.get_text(separator="\n")
            
            # Limpar espaços extras
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            logger.warning(f"Erro ao limpar HTML: {e}")
            return html_content

    def obter_url_pdf_diario(self, diario_id: str) -> Optional[str]:
        """Obtém URL de download do PDF de um diário específico."""
        url = f"{self.BASE_URL}/diario/{diario_id}/download"
        response = self._fazer_requisicao("HEAD", url)
        if response and response.status_code == 200:
            return url
        return None

    def _parse_json_response(self, data: dict, dt: date) -> list[DiarioItem]:
        """Parseia resposta JSON do DJEN."""
        items = []

        # Estrutura pode variar - tentamos formatos conhecidos
        diarios = data if isinstance(data, list) else data.get("diarios", [])

        for diario in diarios:
            try:
                item = DiarioItem(
                    tribunal=self.tribunal,
                    data_publicacao=dt,
                    caderno=str(diario.get("caderno", "")),
                    caderno_nome=diario.get("descricaoCaderno", ""),
                    url_pdf=urljoin(
                        self.BASE_URL,
                        diario.get("linkDownload", diario.get("url", "")),
                    ),
                    edicao=str(diario.get("numero", diario.get("edicao", ""))),
                    num_paginas=diario.get("quantidadePaginas", 0),
                    metadata={"fonte": "DJEN", "diario_id": diario.get("id")},
                )
                items.append(item)
            except Exception as e:
                logger.warning(f"Erro ao parsear diário DJEN: {e}")

        return items

    def _parse_html_response(self, html: str, dt: date) -> list[DiarioItem]:
        """Parseia resposta HTML do DJEN."""
        items = []
        soup = BeautifulSoup(html, "html.parser")

        # Busca links de download de diários
        # Padrões comuns no DJEN:
        # - Links com classe específica
        # - Tabelas com listagem de edições
        for link in soup.select("a[href*='download'], a[href*='diario']"):
            href = link.get("href", "")
            if not href:
                continue

            texto = link.get_text(strip=True)
            url_pdf = urljoin(self.BASE_URL, href)

            # Tentar extrair número do caderno do texto ou atributos
            caderno = self._extrair_caderno(link, texto)
            edicao = self._extrair_edicao(link, texto)

            item = DiarioItem(
                tribunal=self.tribunal,
                data_publicacao=dt,
                caderno=caderno,
                caderno_nome=texto,
                url_pdf=url_pdf,
                edicao=edicao,
                metadata={"fonte": "DJEN"},
            )
            items.append(item)

        return items

    def _parse_busca_json(self, data: dict, termo: str) -> list[dict]:
        """Parseia resultados de busca JSON."""
        resultados = []
        items = data if isinstance(data, list) else data.get("resultados", [])

        for item in items:
            resultados.append(
                {
                    "tribunal": self.tribunal,
                    "data": item.get("dataPublicacao", ""),
                    "caderno": item.get("caderno", ""),
                    "texto": item.get("conteudo", item.get("texto", "")),
                    "url": urljoin(self.BASE_URL, item.get("link", "")),
                    "termo_buscado": termo,
                    "fonte": "DJEN",
                }
            )

        return resultados

    def _parse_busca_html(self, html: str, termo: str) -> list[dict]:
        """Parseia resultados de busca HTML."""
        resultados = []
        soup = BeautifulSoup(html, "html.parser")

        # Busca por elementos que contenham resultados
        # Busca por elementos que contenham resultados (cards de comunicação)
        # Adaptado para o layout da imagem (cards com azul no topo)
        for card in soup.select("div.card, div.resultado, app-comunicacao-card"):
            texto_full = card.get_text(" ", strip=True)
            
            # Tentar extrair número do processo (padrão NNNNNNN-DD.AAAA.J.TR.OOOO)
            proc_match = re.search(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}", texto_full)
            processo = proc_match.group(0) if proc_match else ""

            # Extrair data (DD/MM/AAAA)
            data_match = re.search(r"\d{2}/\d{2}/\d{4}", texto_full)
            data_disp = data_match.group(0) if data_match else ""
            
            # Extrair órgão (geralmente logo no início ou após rótulo)
            orgao = ""
            if "Órgão:" in texto_full:
                parts = texto_full.split("Órgão:")
                if len(parts) > 1:
                    orgao = parts[1].split("\n")[0].split("Data")[0].strip()

            resultados.append(
                {
                    "tribunal": self.tribunal,
                    "processo": processo,
                    "data_disponibilizacao": data_disp,
                    "orgao": orgao,
                    "texto": texto_full[:3000], # Limitar tamanho
                    "termo_buscado": termo,
                    "fonte": "DJEN HTML",
                }
            )

        return resultados

    def _extrair_caderno(self, element, texto: str) -> str:
        """Tenta extrair identificador do caderno."""
        # Busca em atributos data-*
        for attr in element.attrs:
            if "caderno" in attr.lower():
                return str(element[attr])

        # Busca no texto
        match = re.search(r"caderno\s*(\d+)", texto, re.IGNORECASE)
        if match:
            return match.group(1)

        return "0"

    def _extrair_edicao(self, element, texto: str) -> str:
        """Tenta extrair número da edição."""
        for attr in element.attrs:
            if "edicao" in attr.lower() or "numero" in attr.lower():
                return str(element[attr])

        match = re.search(r"(?:edi[çc][aã]o|n[úu]mero)\s*(\d+)", texto, re.IGNORECASE)
        if match:
            return match.group(1)

        return ""
