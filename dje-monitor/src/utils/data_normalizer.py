"""
Script de utilidade para normalizar e filtrar dados de publicações do DJEN.
Foca nos campos estritamente solicitados pelo usuário para integridade de arquitetura.
"""

import re
import hashlib
from datetime import datetime
from typing import Dict, Any, List
from bs4 import BeautifulSoup

def limpar_html(texto: str) -> str:
    """Remove tags HTML e normaliza espaços."""
    if not texto:
        return ""
    if "<" in texto and ">" in texto:
        try:
            soup = BeautifulSoup(texto, "html.parser")
            return " ".join(soup.get_text(separator=" ", strip=True).split())
        except Exception:
            pass
    return " ".join(texto.split())

def extrair_numero_processo(texto: str) -> str:
    """Tenta extrair número do processo padrão CNJ (NNNNNNN-DD.AAAA.J.TR.OOOO) do texto."""
    match = re.search(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}", texto)
    if match:
        return match.group(0)
    return ""

def normalizar_data(data_str: str) -> str:
    """Padroniza a data para YYYY-MM-DD se possível, ou retorna original."""
    if not data_str:
        return ""
    # Tenta formatos comuns
    # Tenta formatos comuns
    clean_date = data_str.strip()
    if not clean_date:
         return ""
         
    formatos = [
        "%Y-%m-%d", 
        "%d/%m/%Y", 
        "%Y-%m-%dT%H:%M:%S", 
        "%Y-%m-%dT%H:%M:%S.%fZ", # UTC
        "%Y-%m-%dT%H:%M:%S.%f"
    ]
    
    # Se tiver separador T, pega só a primeira parte
    if "T" in clean_date:
        parte_data = clean_date.split("T")[0]
        try:
             return datetime.strptime(parte_data, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
             pass

    for fmt in formatos:
        try:
            dt = datetime.strptime(clean_date, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
            
    return data_str

def extrair_resumo_simples(texto_completo: str) -> str:
    """Gera um resumo limpo do texto."""
    texto = limpar_html(texto_completo)
    return texto[:300] + ("..." if len(texto) > 300 else "")

def filtrar_dados_relevantes(item_bruto: Dict[str, Any], termo_monitorado: str) -> Dict[str, Any]:
    """
    Transforma o JSON bruto do DJEN no formato estruturado solicitado.
    
    Campos Obrigatórios:
    - numero_processo: Chave de busca.
    - data_disponibilizacao: Gatilho de contagem de prazo.
    - destinatarios: Filtro para saber qual cliente alertar.
    - tipoComunicacao: Classificação do tipo de alerta.
    - siglaTribunal: Organização regional.
    - nomeOrgao: Localização física/setorial.
    """
    
    texto_completo = item_bruto.get("texto", "") or item_bruto.get("conteudo", "")
    
    
    # 1. numero_processo (Crítica)
    # Tenta pegar do campo formatado primeiro, depois normal, depois processo
    proc = (
        item_bruto.get("numeroprocessocommascara") or 
        item_bruto.get("numero_processo") or 
        item_bruto.get("processo") or ""
    )
    if not proc:
        proc = extrair_numero_processo(texto_completo)
    
    # 2. data_disponibilizacao (Crítica)
    data_raw = (
        item_bruto.get("data_disponibilizacao") or 
        item_bruto.get("datadisponibilizacao") or 
        item_bruto.get("dataDisponibilizacao") or ""
    )
    data_disp = normalizar_data(data_raw)
    
    # Se ainda nulo, tentar extrair regex do texto
    if not data_disp or data_disp == "":
         match_dt = re.search(r"\d{2}/\d{2}/\d{4}", texto_completo)
         if match_dt:
             data_disp = normalizar_data(match_dt.group(0))
             
    if not data_disp:
        data_disp = "[S/D]"
    
    # 3. destinatarios (Alta)
    raw_dest = item_bruto.get("destinatarios") or item_bruto.get("partes", [])
    if raw_dest:
        if isinstance(raw_dest, list):
            # Pode ser lista de strings ou lista de objetos com 'nome'
            destinatarios = []
            for d in raw_dest:
                if isinstance(d, dict) and "nome" in d:
                    destinatarios.append(d["nome"])
                elif isinstance(d, str):
                    destinatarios.append(d)
                else:
                    destinatarios.append(str(d))
        else:
            destinatarios = [str(raw_dest)]
    else:
        destinatarios = []

    if not destinatarios and "destinatario" in item_bruto:
         destinatarios = [item_bruto["destinatario"]]
            
    # 4. tipoComunicacao (Alta)
    # Tenta vários campos que podem indicar o tipo
    tipo_comunicacao = (
        item_bruto.get("tipoComunicacao") or 
        item_bruto.get("tipo_comunicacao") or 
        item_bruto.get("tipoDocumento") or
        item_bruto.get("nomeClasse") or
        "COMUNICACAO_GERAL"
    )
    
    if not tipo_comunicacao or tipo_comunicacao == "N/A":
         # Tenta inferir do texto se ainda nulo
         lower_text = texto_completo.lower()
         if "intima" in lower_text: tipo_comunicacao = "INTIMACAO"
         elif "cita" in lower_text: tipo_comunicacao = "CITACAO"
         elif "despacho" in lower_text: tipo_comunicacao = "DESPACHO"
         elif "sentença" in lower_text: tipo_comunicacao = "SENTENCA"
         elif "acórdão" in lower_text: tipo_comunicacao = "ACORDAO"
    
    # 5. siglaTribunal (Média)
    tribunal = item_bruto.get("siglaTribunal") or item_bruto.get("tribunal") or ""

    # 6. nomeOrgao (Média)
    orgao = item_bruto.get("nomeOrgao") or item_bruto.get("orgao") or ""

    return {
        "numero_processo": proc,
        "data_disponibilizacao": data_disp,
        "destinatarios": destinatarios,
        "tipoComunicacao": tipo_comunicacao,
        "siglaTribunal": tribunal,
        "nomeOrgao": orgao,
        # Campo extra para exibição do resumo
        "texto_resumo": extrair_resumo_simples(texto_completo) 
    }
