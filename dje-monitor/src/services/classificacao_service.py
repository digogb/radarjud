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

Dadas publicações recentes do DJe sobre um processo, determine:
1. O PAPEL da parte monitorada neste processo específico (credora ou devedora)
2. Se há crédito a receber pela parte monitorada

Sinais de CREDOR: alvará/mandado de levantamento EM FAVOR da parte, precatório a receber, \
RPV, acordo em que a parte recebe, depósito judicial a ser levantado pela parte.

Sinais de DEVEDOR: intimação para pagar/depositar, penhora de bens da parte, \
cumprimento de sentença contra a parte, condenação da parte a pagar.

Responda APENAS neste formato (sem explicação adicional):
PAPEL: [CREDOR | DEVEDOR | INDEFINIDO]
VEREDICTO: [CREDITO_IDENTIFICADO | CREDITO_POSSIVEL | SEM_CREDITO]
VALOR: [valor em reais ou "não identificado"]
JUSTIFICATIVA: [1 frase curta]\
"""

_MAX_CHARS_POR_PUB = 500
_MAX_PUBS = 3

_RE_PAPEL = re.compile(r"PAPEL:\s*(CREDOR|DEVEDOR|INDEFINIDO)", re.IGNORECASE)
_RE_VEREDICTO = re.compile(
    r"VEREDICTO:\s*(CREDITO_IDENTIFICADO|CREDITO_POSSIVEL|SEM_CREDITO)",
    re.IGNORECASE,
)
_RE_VALOR = re.compile(r"VALOR:\s*(.+)", re.IGNORECASE)
_RE_JUSTIFICATIVA = re.compile(r"JUSTIFICATIVA:\s*(.+)", re.IGNORECASE)


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


def classificar_processo(
    publicacoes: list[dict],
    api_key: str,
    modelo: str,
    pessoa_nome: str | None = None,
    numero_processo: str | None = None,
    max_pubs: int = _MAX_PUBS,
    max_chars: int = _MAX_CHARS_POR_PUB,
) -> dict:
    """Classifica credor/devedor a partir das publicações mais recentes.

    Args:
        publicacoes: lista de dicts com campos data_disponibilizacao, texto_completo, etc.
                     Deve estar ordenada por data ASC (mais antiga primeiro).
        api_key: chave da OpenAI.
        modelo: modelo a usar (ex: gpt-4o-mini).
        pessoa_nome: nome da pessoa monitorada.
        numero_processo: número do processo.
        max_pubs: quantas publicações enviar (do final = mais recentes).
        max_chars: limite de caracteres por publicação.

    Returns:
        Dict com chaves: papel, veredicto, valor, justificativa.

    Raises:
        RuntimeError: se a chamada à API falhar.
    """
    from openai import OpenAI

    if not publicacoes:
        return {
            "papel": "INDEFINIDO",
            "veredicto": None,
            "valor": None,
            "justificativa": "Nenhuma publicação encontrada.",
        }

    # Usar as publicações mais recentes (últimas N da lista ordenada ASC)
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
        texto = texto[:max_chars]
        linhas.append(f"\n[{data}] {tipo} — {orgao}\n{texto}")

    conteudo = "\n".join(linhas)

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=modelo,
            messages=[
                {"role": "system", "content": _SISTEMA},
                {"role": "user", "content": conteudo},
            ],
            temperature=0.1,
            max_tokens=200,
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
    """Parseia a resposta estruturada da LLM."""
    result = {
        "papel": "INDEFINIDO",
        "veredicto": None,
        "valor": None,
        "justificativa": None,
    }

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

    return result
