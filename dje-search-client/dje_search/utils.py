"""
Funções utilitárias para normalização e extração de dados de publicações DJE.
"""

import re
import ssl
import unicodedata

from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# SSL
# ---------------------------------------------------------------------------

def create_legacy_ssl_context() -> ssl.SSLContext:
    """
    Cria contexto SSL compatível com servidores governamentais legados.

    Tribunais como o TJCE usam cifras antigas (AES256-SHA) que são rejeitadas
    pelo padrão do OpenSSL 3.x. Este contexto relaxa as restrições para permitir
    a conexão.
    """
    ctx = ssl.create_default_context()
    try:
        ctx.set_ciphers("DEFAULT:AES256-SHA:AES128-SHA:@SECLEVEL=1")
        if hasattr(ssl, "OP_LEGACY_SERVER_CONNECT"):
            ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
    except Exception:
        pass
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


# ---------------------------------------------------------------------------
# Texto
# ---------------------------------------------------------------------------

def normalizar_nome(nome: str) -> str:
    """
    Normaliza nome para comparação sem diferenciação de acentos ou caixa.

    Exemplos::

        normalizar_nome("JOÃO DA SILVA")  # → "JOAO DA SILVA"
        normalizar_nome("josé ribeiro")   # → "JOSE RIBEIRO"
    """
    if not nome:
        return ""
    decomposto = unicodedata.normalize("NFKD", nome)
    sem_acento = "".join(c for c in decomposto if unicodedata.category(c) != "Mn")
    return sem_acento.strip().upper()


def limpar_html(html_content: str) -> str:
    """
    Remove tags HTML e retorna texto legível com quebras de linha preservadas.
    """
    if not html_content:
        return ""
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        for tag in soup(["script", "style", "header", "footer", "nav"]):
            tag.decompose()
        for br in soup.find_all("br"):
            br.replace_with("\n")
        for tag in soup.find_all(["p", "div", "li", "tr"]):
            tag.insert_after("\n")
        text = soup.get_text(separator="\n")
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        return "\n".join(chunk for chunk in chunks if chunk)
    except Exception:
        return html_content


def extrair_numero_processo(texto: str) -> str:
    """Extrai número de processo no padrão CNJ (NNNNNNN-DD.AAAA.J.TR.OOOO) do texto."""
    match = re.search(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}", texto)
    return match.group(0) if match else ""


# ---------------------------------------------------------------------------
# Extração de polos do texto (fallback quando a API não retorna dados estruturados)
# ---------------------------------------------------------------------------

_POLO_PATTERNS = {
    "ativo": [
        r"(?:AUTOR|EXEQUENTE|REQUERENTE|IMPETRANTE|EMBARGANTE|SUSCITANTE|APELANTE|AGRAVANTE|RECORRENTE)"
        r"[AEIS]*\s*[:]\s*([^:\n]{3,180})"
    ],
    "passivo": [
        r"(?:R[ÉE]U|EXECUTADO|REQUERIDO|IMPETRADO|EMBARGADO|SUSCITADO|APELADO|AGRAVADO|RECORRIDO)"
        r"[AEIS]*\s*[:]\s*([^:\n]{3,180})"
    ],
    "outros": [
        r"(?:ADVOGAD[OA]|PATRONO)[S]*\s*[:]\s*([^:\n]{3,180})"
    ],
}

_STOP_WORDS = {"A", "O", "OS", "AS", "DE", "DA", "DO", "EM", "NA", "NO"}


def extrair_polos_do_texto(texto: str) -> dict:
    """
    Extrai polos ativo, passivo e outros do texto da publicação via regex.

    Usado como fallback quando a API não retorna dados estruturados de partes.
    Retorna dict com chaves ``ativo``, ``passivo`` e ``outros``.
    """
    if not texto:
        return {"ativo": [], "passivo": [], "outros": []}

    polos: dict[str, list[str]] = {"ativo": [], "passivo": [], "outros": []}
    texto_upper = texto.upper()

    def _limpar(raw: str) -> str:
        token = re.split(
            r"\s-\s|ADVOGAD|R[ÉE]U|AUTOR|JUIZ|OAB|CPF|CNPJ|\.\s|;|(?:\s\w{2}\s)", raw
        )
        return token[0].strip().title()

    for tipo, patterns in _POLO_PATTERNS.items():
        for pat in patterns:
            for match in re.finditer(pat, texto_upper):
                for nome_bruto in match.group(1).split(","):
                    nome = _limpar(nome_bruto)
                    if (
                        3 < len(nome) < 80
                        and len(nome.split()) <= 10
                        and nome.upper() not in _STOP_WORDS
                        and nome not in polos[tipo]
                    ):
                        polos[tipo].append(nome)

    return polos
