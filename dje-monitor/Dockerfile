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

# Instalar dependências Python
COPY requirements.txt .
# torch CPU-only primeiro (reduz imagem ~1GB vs versão GPU)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

# Pré-download do modelo Nomic (evita download no primeiro request em produção)
# Remova esta linha se quiser imagem menor e aceitar download no primeiro boot do worker
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('nomic-ai/nomic-embed-text-v1.5', trust_remote_code=True)" || \
    echo 'Aviso: pré-download do modelo falhou, será baixado no primeiro uso'

# Copiar código fonte
COPY src/ ./src/

# Criar diretório de dados
RUN mkdir -p /app/data/pdfs

WORKDIR /app/src

ENTRYPOINT ["python", "main.py"]
CMD ["scheduler"]
