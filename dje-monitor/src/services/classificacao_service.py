"""
Serviço de classificação automática de credor/devedor via OpenAI.

Prompt curto e otimizado para batch: recebe as publicações mais recentes de um
processo e determina se a parte monitorada é credora ou devedora, com custo
mínimo de tokens (~50-80 tokens de output).
"""

import json
import logging
import re

logger = logging.getLogger(__name__)

_SISTEMA = """\
Você é um analista jurídico especializado em execuções judiciais brasileiras.

Dadas publicações do DJe sobre um processo, determine DUAS coisas de forma INDEPENDENTE:

1. PAPEL — deriva APENAS da posição processual da parte monitorada, NÃO da existência de crédito:
   - CREDOR: exequente, autor/requerente em ação de cobrança/execução, apelante que busca
     receber, beneficiário de alvará/levantamento/precatório/RPV.
   - DEVEDOR: executado, réu/requerido em execução ou cumprimento de sentença, parte
     intimada a pagar/depositar, parte que sofre penhora ou condenação a pagar.
   - INDEFINIDO: quando a posição não puder ser determinada pelas publicações.
   REGRA: nunca classifique como DEVEDOR só porque não há sinal de crédito. Ausência de
   crédito NÃO torna a parte devedora — se ela é autora/exequente, o papel é CREDOR.

2. VEREDICTO — indica se há crédito concreto a receber:
   - CREDITO_IDENTIFICADO: há alvará/mandado de levantamento, precatório, RPV ou valor
     líquido em favor da parte.
   - CREDITO_POSSIVEL: a parte está no polo credor (exequente/autora de cobrança) e há
     indício de recebimento futuro, mas sem valor/levantamento já formalizado.
   - SEM_CREDITO: parte devedora, ou nenhum indício de recebimento.
   REGRA: se a parte é CREDOR e há qualquer sinal de levantamento/pagamento/execução em seu
   favor (ex.: art. 523, cumprimento de sentença movido por ela), classifique no MÍNIMO
   como CREDITO_POSSIVEL — não use SEM_CREDITO nesse caso.

3. VALOR — o valor em reais a receber, quando houver menção explícita:
   - "valor": texto como aparece (ex.: "R$ 15.000,00") ou "não identificado".
   - "valor_numerico": o MESMO valor como número decimal (ex.: 15000.00), ou null se
     não identificado. Use ponto como separador decimal, sem separador de milhar.\
"""

_MAX_CHARS_POR_PUB = 2000
_MAX_PUBS = 5

# Schema para structured outputs (elimina erros de parsing e já entrega valor_numerico).
_RESPONSE_SCHEMA = {
    "name": "classificacao_processo",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "papel": {"type": "string", "enum": ["CREDOR", "DEVEDOR", "INDEFINIDO"]},
            "veredicto": {
                "type": "string",
                "enum": ["CREDITO_IDENTIFICADO", "CREDITO_POSSIVEL", "SEM_CREDITO"],
            },
            "valor": {"type": "string"},
            "valor_numerico": {"type": ["number", "null"]},
            "justificativa": {"type": "string"},
        },
        "required": ["papel", "veredicto", "valor", "valor_numerico", "justificativa"],
    },
}

# Fallback regex (usado só se a resposta não vier como JSON válido).
_RE_PAPEL = re.compile(r"PAPEL:\s*(CREDOR|DEVEDOR|INDEFINIDO)", re.IGNORECASE)
_RE_VEREDICTO = re.compile(
    r"VEREDICTO:\s*(CREDITO_IDENTIFICADO|CREDITO_POSSIVEL|SEM_CREDITO)",
    re.IGNORECASE,
)
_RE_VALOR = re.compile(r"VALOR:\s*(.+)", re.IGNORECASE)
_RE_JUSTIFICATIVA = re.compile(r"JUSTIFICATIVA:\s*(.+)", re.IGNORECASE)


def _parse_valor_brl(texto: "str | None") -> "float | None":
    """Extrai o primeiro valor monetário pt-BR de um texto como float.

    'R$ 1.234.567,89' → 1234567.89 · 'R$ 800' → 800.0 · 'não identificado' → None
    """
    if not texto:
        return None
    m = re.search(r"(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:,\d{1,2})?)", texto)
    if not m:
        return None
    s = m.group(1).replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _extrair_partes(publicacoes: list[dict]) -> dict[str, list[str]]:
    """Agrega partes únicas (ativo/passivo) de todas as publicações."""
    ativo: set[str] = set()
    passivo: set[str] = set()
    for pub in publicacoes:
        try:
            polos = json.loads(pub.get("polos_json") or "{}")
        except (ValueError, TypeError):
            continue
        for nome in polos.get("ativo", []):
            if nome.strip():
                ativo.add(nome.strip())
        for nome in polos.get("passivo", []):
            if nome.strip():
                passivo.add(nome.strip())
    return {"ativo": sorted(ativo), "passivo": sorted(passivo)}


def _tem_padrao(pub: dict, padroes: list[str]) -> bool:
    """True se o texto da publicação contém algum padrão positivo."""
    texto = ((pub.get("texto_completo") or "") + " " + (pub.get("texto_resumo") or "")).lower()
    return any(p.lower() in texto for p in padroes)


def _extrair_janela(texto: str, padroes: list[str], max_chars: int) -> str:
    """Retorna um trecho de ~max_chars centrado no primeiro padrão positivo.

    Garante que o sinal que disparou a oportunidade (ex.: "alvará de levantamento")
    entre no contexto enviado à IA, em vez de cortar sempre o início do texto.
    Sem match, devolve o começo do texto.
    """
    if not texto:
        return ""
    if len(texto) <= max_chars:
        return texto
    txt_lower = texto.lower()
    pos = -1
    for pad in padroes or []:
        idx = txt_lower.find(pad.lower())
        if idx != -1 and (pos == -1 or idx < pos):
            pos = idx
    if pos == -1:
        return texto[:max_chars]
    antes = min(300, max_chars // 4)
    inicio = max(0, pos - antes)
    fim = min(len(texto), inicio + max_chars)
    trecho = texto[inicio:fim]
    return ("…" if inicio > 0 else "") + trecho + ("…" if fim < len(texto) else "")


def classificar_processo(
    publicacoes: list[dict],
    api_key: str,
    modelo: str,
    pessoa_nome: str | None = None,
    numero_processo: str | None = None,
    max_pubs: int = _MAX_PUBS,
    max_chars: int = _MAX_CHARS_POR_PUB,
    padroes_positivos: list[str] | None = None,
) -> dict:
    """Classifica credor/devedor a partir das publicações mais recentes.

    Args:
        publicacoes: lista de dicts com campos data_disponibilizacao, texto_completo, etc.
                     Deve estar ordenada por data ASC (mais antiga primeiro).
        api_key: chave da OpenAI.
        modelo: modelo a usar (ex: gpt-4o-mini).
        pessoa_nome: nome da pessoa monitorada.
        numero_processo: número do processo.
        max_pubs: quantas publicações enviar.
        max_chars: limite de caracteres por publicação.
        padroes_positivos: expressões dos padrões de oportunidade ativos. Usadas para
                     (a) priorizar as publicações que contêm o sinal e (b) centrar o
                     recorte de texto no sinal, evitando cortá-lo do contexto.

    Returns:
        Dict com chaves: papel, veredicto, valor, justificativa.

    Raises:
        RuntimeError: se a chamada à API falhar.
    """
    padroes_positivos = padroes_positivos or []
    from openai import OpenAI

    if not publicacoes:
        return {
            "papel": "INDEFINIDO",
            "veredicto": None,
            "valor": None,
            "valor_numerico": None,
            "justificativa": "Nenhuma publicação encontrada.",
        }

    # Selecionar publicações a enviar: priorizar as que contêm o sinal positivo
    # (é nelas que está a evidência de crédito), completando com as mais recentes.
    # Mantém a ordem cronológica (publicacoes já vem ASC).
    if padroes_positivos:
        idx_com_sinal = [i for i, p in enumerate(publicacoes) if _tem_padrao(p, padroes_positivos)]
        idx_sel = set(idx_com_sinal[-max_pubs:])
        for i in range(len(publicacoes) - 1, -1, -1):
            if len(idx_sel) >= max_pubs:
                break
            idx_sel.add(i)
        recentes = [p for i, p in enumerate(publicacoes) if i in idx_sel]
    else:
        recentes = publicacoes[-max_pubs:]

    # Montar contexto
    partes = _extrair_partes(publicacoes)
    linhas = []
    if pessoa_nome:
        linhas.append(f"Parte monitorada: {pessoa_nome}")
    if numero_processo:
        linhas.append(f"Processo: {numero_processo}")
    if partes["ativo"]:
        linhas.append(f"Polo ativo: {', '.join(partes['ativo'])}")
    if partes["passivo"]:
        linhas.append(f"Polo passivo: {', '.join(partes['passivo'])}")

    linhas.append("")
    linhas.append("Publicações mais recentes:")

    for pub in recentes:
        data = pub.get("data_disponibilizacao", "")
        orgao = pub.get("orgao", "")
        tipo = pub.get("tipo_comunicacao", "")
        texto = (pub.get("texto_completo") or pub.get("texto_resumo") or "").strip()
        texto = _extrair_janela(texto, padroes_positivos, max_chars)
        linhas.append(f"\n[{data}] {tipo} — {orgao}\n{texto}")

    conteudo = "\n".join(linhas)

    messages = [
        {"role": "system", "content": _SISTEMA},
        {"role": "user", "content": conteudo},
    ]

    try:
        client = OpenAI(api_key=api_key)
        try:
            response = client.chat.completions.create(
                model=modelo,
                messages=messages,
                temperature=0.1,
                max_tokens=250,
                response_format={"type": "json_schema", "json_schema": _RESPONSE_SCHEMA},
            )
        except Exception as e:
            # Fallback: modelo/endpoint sem suporte a structured outputs → texto simples.
            logger.warning(f"classificar_processo: structured output indisponível ({e}); usando texto.")
            response = client.chat.completions.create(
                model=modelo,
                messages=messages,
                temperature=0.1,
                max_tokens=250,
            )
        texto_resp = response.choices[0].message.content or ""

        # Log de tokens para monitoramento de custo
        usage = response.usage
        if usage:
            logger.info(
                f"classificar_processo: tokens input={usage.prompt_tokens} "
                f"output={usage.completion_tokens} total={usage.total_tokens} "
                f"modelo={modelo}"
            )

        return _parsear_resposta(texto_resp)
    except Exception as e:
        logger.error(f"classificar_processo: erro na chamada OpenAI: {e}")
        raise RuntimeError(f"Erro ao classificar processo: {e}") from e


def _parsear_resposta(texto: str) -> dict:
    """Parseia a resposta da LLM. Tenta JSON (structured output); cai para regex."""
    result = {
        "papel": "INDEFINIDO",
        "veredicto": None,
        "valor": None,
        "valor_numerico": None,
        "justificativa": None,
    }

    # Caminho principal: JSON (structured outputs).
    try:
        data = json.loads(texto)
        if isinstance(data, dict):
            papel = (data.get("papel") or "INDEFINIDO")
            result["papel"] = str(papel).upper()
            ver = data.get("veredicto")
            result["veredicto"] = str(ver).upper() if ver else None
            result["valor"] = data.get("valor")
            vn = data.get("valor_numerico")
            result["valor_numerico"] = (
                float(vn) if isinstance(vn, (int, float))
                else _parse_valor_brl(result["valor"])
            )
            result["justificativa"] = data.get("justificativa")
            return result
    except (ValueError, TypeError):
        pass

    # Fallback: formato texto legado (PAPEL:/VEREDICTO:/...).
    m = _RE_PAPEL.search(texto)
    if m:
        result["papel"] = m.group(1).upper()

    m = _RE_VEREDICTO.search(texto)
    if m:
        result["veredicto"] = m.group(1).upper()

    m = _RE_VALOR.search(texto)
    if m:
        result["valor"] = m.group(1).strip()

    m = _RE_JUSTIFICATIVA.search(texto)
    if m:
        result["justificativa"] = m.group(1).strip()

    result["valor_numerico"] = _parse_valor_brl(result["valor"])
    return result
