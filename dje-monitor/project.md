# DJE Monitor - Project Context

## Visão Geral
**DJE Monitor** é um sistema automatizado desenvolvido em Python para monitorar o Diário da Justiça Eletrônico (DJe/DJEN). O sistema coleta publicações de tribunais (focado inicialmente no TJCE), extrai o conteúdo dos PDFs (com suporte a OCR para arquivos digitalizados) e busca por menções a CPFs cadastrados. Quando uma ocorrência é encontrada, notificações são enviadas via Telegram e Email.

## Principais Funcionalidades
1.  **Coleta Automatizada**:
    *   Suporte a diários do tipo DJEN e e-SAJ.
    *   Configurável por tribunal.
    *   Suporte a dias retroativos.
2.  **Processamento de PDF**:
    *   Download automático de cadernos.
    *   Verificação de integridade (hash).
    *   Extração de texto via `PyMuPDF`.
    *   **OCR Automático**: Utiliza `Tesseract` quando detecta que o PDF é escaneado (baixa densidade de texto).
3.  **Monitoramento de CPFs**:
    *   Busca exata por CPFs normalizados.
    *   Base de dados SQLite para armazenar CPFs, Diários e Ocorrências.
4.  **Notificações**:
    *   **Telegram**: Mensagens instantâneas com detalhes da ocorrência.
    *   **Email**: Alertas por email via SMTP.
5.  **Interface de Linha de Comando (CLI)**:
    *   Gerenciamento de CPFs (adicionar, remover, listar).
    *   Visualização de ocorrências e status.
    *   Modo `scheduler` para execução contínua.

## Arquitetura do Projeto

### Estrutura de Diretórios
```
dje-monitor/
├── src/
│   ├── collectors/   # Lógica de scraping (DJEN, e-SAJ)
│   ├── extractors/   # Extração de dados (PDF, OCR)
│   ├── matchers/     # Busca de padrões (CPFs)
│   ├── notifiers/    # Canais de notificação (Telegram, Email)
│   ├── storage/      # Banco de dados e Models (SQLAlchemy)
│   ├── config.py     # Gerenciamento de configurações e variáveis de ambiente
│   └── main.py       # Ponto de entrada (CLI e Scheduler)
├── data/             # Armazenamento local (DB SQLite, PDFs baixados)
├── tests/            # Testes automatizados (pytest)
├── Dockerfile        # Configuração para containerização
└── docker-compose.yml # Orquestração de containers
```

### Tecnologias Principais
*   **Linguagem**: Python 3.10+
*   **Web Scraping**: `httpx`, `beautifulsoup4`
*   **PDF/OCR**: `PyMuPDF` (`fitz`), `pytesseract`, `pdfplumber`, `Pillow`
*   **Banco de Dados**: `SQLAlchemy` (SQLite por padrão)
*   **Agendamento**: `APScheduler`
*   **CLI**: `rich`, `argparse`

## Configuração (Variáveis de Ambiente)
O sistema é configurado via arquivo `.env` ou variáveis de ambiente. As principais chaves (definidas em `src/config.py`) são:

*   **Geral**:
    *   `DJE_TRIBUNAL`: Tribunal alvo (padrão: TJCE).
    *   `DJE_CPFS_MONITORADOS`: Lista inicial de CPFs (separados por vírgula).
*   **Feature Flags**:
    *   `DJE_USAR_DJEN`: Habilita busca no DJEN.
    *   `DJE_USAR_ESAJ`: Habilita busca no e-SAJ.
    *   `DJE_MODO_SCHEDULER`: Ativa modo de agendamento contínuo.
*   **Notificações**:
    *   `DJE_TELEGRAM_BOT_TOKEN` / `DJE_TELEGRAM_CHAT_ID`: Configuração do bot Telegram.
    *   `DJE_SMTP_HOST` / `DJE_SMTP_USER` / `DJE_SMTP_PASSWORD`: Configuração de envio de emails.
*   **OCR**:
    *   `DJE_OCR_LANG`: Idioma para OCR (padrão: 'por').
    *   `DJE_OCR_DPI`: Qualidade da rasterização para OCR.

## Como Executar

### Via CLI (Local)
```bash
# Instalar dependências
pip install -r requirements.txt

# Executar monitoramento manual
python src/main.py executar

# Adicionar CPF
python src/main.py adicionar-cpf 12345678900 --nome "Fulano de Tal"

# Ver Status
python src/main.py status
```

### Via Docker
```bash
docker-compose up -d
```
O container executará em modo `scheduler` se a variável `DJE_MODO_SCHEDULER=true` estiver definida.
