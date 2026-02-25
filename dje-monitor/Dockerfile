FROM python:3.11-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-por \
    libpq-dev \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && sed -i 's/SECLEVEL=2/SECLEVEL=1/g' /etc/ssl/openssl.cnf

WORKDIR /app

# --- Camadas estáveis (raramente mudam — cache independente do requirements.txt) ---
# torch CPU-only (reduz imagem ~1GB vs versão GPU)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Pré-instalar sentence-transformers para cachear o download do modelo separadamente
RUN pip install --no-cache-dir sentence-transformers einops

# Pré-download do modelo Nomic (evita download no primeiro request em produção)
# Esta camada só invalida se as linhas acima mudarem, não quando requirements.txt muda
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('nomic-ai/nomic-embed-text-v1.5', trust_remote_code=True)" || \
    echo 'Aviso: pré-download do modelo falhou, será baixado no primeiro uso'

# --- Camadas que mudam com o código ---
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Criar diretórios (src será montado via volume em runtime)
RUN mkdir -p /app/data/pdfs /app/src

WORKDIR /app/src

ENTRYPOINT ["python", "main.py"]
CMD ["scheduler"]
