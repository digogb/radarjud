"""
Serviço de resumo de processo via OpenAI.

Recebe as publicações de um processo e gera um resumo estruturado da linha do tempo,
incluindo veredito parseável, papel da parte monitorada e valores identificados.
"""

import json
import logging
import re

logger = logging.getLogger(__name__)

_SISTEMA = """\
Você é um assistente jurídico especializado em direito processual brasileiro.
Receberá dados de um processo judicial — partes identificadas e publicações do DJe em ordem cronológica.

Sua tarefa:
1. Identificar explicitamente o papel da parte monitorada neste processo (autora/exequente/credora OU ré/executada/devedora), com base no contexto das publicações, mesmo que os campos de polo estejam incompletos.
2. Resumir a linha do tempo do processo: objeto da ação, principais decisões e status atual.
3. Se houver menção a valores (depósito judicial, cálculo homologado, precatório, RPV, alvará), extrair o valor aproximado.
4. Ao final, emitir um veredito estruturado sobre crédito a receber pela parte monitorada.

Formato de resposta — use exatamente esta estrutura Markdown:

## Papel da Parte Monitorada
[Descreva em 1-2 frases se ela é autora/credora/exequente ou ré/devedora/executada neste processo, e por quê.]

## Linha do Tempo
[Tópicos cronológicos com as principais movimentações. Use **negrito** para datas e decisões relevantes.]

## Status Atual
[1-2 frases sobre o estado atual do processo.]

## Valor Identificado
[Se encontrou valor: "R$ X.XXX,XX (origem)". Se não encontrou: "Não identificado."]

---
VEREDICTO: [CREDITO_IDENTIFICADO | CREDITO_POSSIVEL | SEM_CREDITO]
PAPEL: [CREDOR | DEVEDOR | INDEFINIDO]
VALOR: [valor em reais ou "não identificado"]

NÃO inclua título com o número do processo. Responda em português.\
"""

# Limite de caracteres por publicação
_MAX_CHARS_POR_PUB = 1500
# Limite total de caracteres das publicações enviados ao modelo
_MAX_CHARS_TOTAL = 12_000

# Regex para extrair o bloco de metadados estruturados
_RE_VEREDICTO = re.compile(
    r"VEREDICTO:\s*(CREDITO_IDENTIFICADO|CREDITO_POSSIVEL|SEM_CREDITO)",
    re.IGNORECASE,
)
_RE_PAPEL = re.compile(r"PAPEL:\s*(CREDOR|DEVEDOR|INDEFINIDO)", re.IGNORECASE)
_RE_VALOR = re.compile(r"VALOR:\s*(.+)", re.IGNORECASE)


def _extrair_partes(publicacoes: list[dict]) -> dict[str, list[str]]:
    """Agrega partes únicas (ativo/passivo) de todas as publicações do processo."""
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


def _parsear_metadata(texto: str) -> tuple[str, dict]:
    """Separa o resumo narrativo dos metadados estruturados ao final do texto.

    Returns:
        (resumo_limpo, metadata) onde metadata tem chaves veredicto, papel, valor.
    """
    meta = {"veredicto": None, "papel": None, "valor": None}

    m = _RE_VEREDICTO.search(texto)
    if m:
        meta["veredicto"] = m.group(1).upper()

    m = _RE_PAPEL.search(texto)
    if m:
        meta["papel"] = m.group(1).upper()

    m = _RE_VALOR.search(texto)
    if m:
        meta["valor"] = m.group(1).strip()

    # Remove o bloco de metadados do texto exibido.
    # Tenta 1: "---" (separador) antes do bloco — com espaço/newlines variáveis entre eles.
    resumo_limpo = re.sub(
        r"\n*-{3,}\s*\n[\s\S]*?VEREDICTO:[\s\S]*$",
        "",
        texto,
        flags=re.IGNORECASE,
    ).strip()
    # Tenta 2 (fallback): sem separador --- — strip direto a partir de VEREDICTO:
    if re.search(r"\bVEREDICTO:", resumo_limpo, re.IGNORECASE):
        resumo_limpo = re.sub(
            r"\n*\bVEREDICTO:[\s\S]*$",
            "",
            resumo_limpo,
            flags=re.IGNORECASE,
        ).strip()

    return resumo_limpo, meta


def gerar_resumo_processo(
    publicacoes: list[dict],
    api_key: str,
    modelo: str,
    pessoa_nome: str | None = None,
    numero_processo: str | None = None,
) -> dict:
    """Gera resumo estruturado do processo a partir das publicações via OpenAI.

    Returns:
        Dict com chaves: resumo (Markdown), veredicto, papel, valor, cache (bool).

    Raises:
        RuntimeError: Se a chamada à API falhar.
    """
    from openai import OpenAI

    if not publicacoes:
        return {
            "resumo": "Nenhuma publicação encontrada para este processo.",
            "veredicto": None,
            "papel": None,
            "valor": None,
        }

    # --- Contexto do processo ---
    partes = _extrair_partes(publicacoes)
    linhas_contexto = ["## Contexto do Monitoramento\n"]
    if numero_processo:
        linhas_contexto.append(f"**Número do processo**: {numero_processo}")
    if pessoa_nome:
        linhas_contexto.append(
            f"**Parte monitorada**: {pessoa_nome} "
            f"(estamos verificando seu papel neste processo — pode ser credora ou devedora)"
        )
    if partes["ativo"]:
        linhas_contexto.append(f"**Polo ativo nas publicações**: {', '.join(partes['ativo'])}")
    if partes["passivo"]:
        linhas_contexto.append(f"**Polo passivo nas publicações**: {', '.join(partes['passivo'])}")

    secao_contexto = "\n".join(linhas_contexto)

    # --- Publicações ---
    blocos = []
    chars_acumulados = 0
    for pub in publicacoes:
        data = pub.get("data_disponibilizacao", "")
        orgao = pub.get("orgao", "")
        tipo = pub.get("tipo_comunicacao", "")
        texto = (pub.get("texto_completo") or pub.get("texto_resumo") or "").strip()
        texto = texto[:_MAX_CHARS_POR_PUB]

        bloco = f"[{data}] {tipo} — {orgao}\n{texto}"
        if chars_acumulados + len(bloco) > _MAX_CHARS_TOTAL:
            blocos.append("... (publicações mais antigas omitidas por limite de tamanho)")
            break
        blocos.append(bloco)
        chars_acumulados += len(bloco)

    secao_pubs = "## Publicações do DJe\n\n" + "\n\n---\n\n".join(blocos)
    conteudo_usuario = f"{secao_contexto}\n\n{secao_pubs}"

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=modelo,
            messages=[
                {"role": "system", "content": _SISTEMA},
                {"role": "user", "content": conteudo_usuario},
            ],
            temperature=0.2,
            max_tokens=1400,
        )
        texto_completo = response.choices[0].message.content or ""
        resumo_limpo, meta = _parsear_metadata(texto_completo)
        return {
            "resumo": resumo_limpo,
            "veredicto": meta["veredicto"],
            "papel": meta["papel"],
            "valor": meta["valor"],
        }
    except Exception as e:
        logger.error(f"gerar_resumo_processo: erro na chamada OpenAI: {e}")
        raise RuntimeError(f"Erro ao gerar resumo: {e}") from e
