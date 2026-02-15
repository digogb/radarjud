# Configuração para Execução Local (fora do container)

Este guia explica como executar o DJE Monitor localmente no WSL2, usando o ComunicaCollector com Selenium.

## 📋 Pré-requisitos

### 1. Instalar Python e dependências do sistema

```bash
# Atualizar pacotes
sudo apt update

# Instalar Python, pip e venv
sudo apt install -y python3.12 python3.12-venv python3-pip

# Instalar Chrome (para Selenium)
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/google-chrome.gpg
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install -y google-chrome-stable

# Instalar Tesseract OCR (para extração de PDF)
sudo apt install -y tesseract-ocr tesseract-ocr-por
```

### 2. Criar ambiente virtual

```bash
cd /home/rodgb/personal/radarjud/dje-monitor

# Criar ambiente virtual
python3 -m venv venv

# Ativar ambiente virtual
source venv/bin/activate

# Instalar dependências Python
pip install --upgrade pip
pip install -r requirements.txt
```

## 🚀 Execução

### Testar o ComunicaCollector

```bash
# Ativar ambiente virtual (se não estiver ativo)
source venv/bin/activate

# Executar teste
python test_comunica.py
```

### Executar monitoramento manual

```bash
source venv/bin/activate
cd src
python main.py executar
```

### Gerenciar CPFs

```bash
source venv/bin/activate
cd src

# Adicionar CPF
python main.py adicionar-cpf 12345678900 --nome "Fulano de Tal"

# Listar CPFs
python main.py listar-cpfs

# Remover CPF
python main.py remover-cpf 12345678900
```

### Executar em modo scheduler (contínuo)

```bash
source venv/bin/activate
cd src
python main.py scheduler
```

## 🐛 Troubleshooting

### Chrome não inicia

Se o Chrome não iniciar, verifique:

```bash
# Verificar instalação do Chrome
google-chrome --version

# Testar Chrome headless
google-chrome --headless --dump-dom https://google.com
```

### Erro de permissões

Se tiver erros de permissão:

```bash
# Dar permissão aos arquivos
chmod +x test_comunica.py
chmod -R u+w data/
```

### Tesseract não encontrado

```bash
# Verificar instalação
tesseract --version

# Reinstalar se necessário
sudo apt install -y tesseract-ocr tesseract-ocr-por
```

## 📝 Configuração

Edite o arquivo `.env` para configurar:

- **DJE_TRIBUNAL**: Tribunal a monitorar (padrão: TJCE)
- **DJE_CPFS_MONITORADOS**: Lista de CPFs separados por vírgula
- **DJE_USAR_DJEN**: Habilitar coleta via DJEN (true/false)
- **DJE_USAR_ESAJ**: Habilitar coleta via e-SAJ (true/false)
- **DJE_TELEGRAM_BOT_TOKEN / DJE_TELEGRAM_CHAT_ID**: Notificações via Telegram
- **DJE_SMTP_***: Configurações de email

## 🔄 Comparação: Local vs Container

### Execução Local (Recomendado para desenvolvimento/testes)
✅ Chrome funciona melhor no WSL2
✅ Mais fácil debug e desenvolvimento
✅ Acesso direto aos arquivos
❌ Precisa instalar dependências manualmente

### Execução em Container (Recomendado para produção)
✅ Ambiente isolado e reproduzível
✅ Fácil deploy em servidores
❌ Chrome pode ter problemas no WSL2
❌ Requer Docker configurado

## 📦 Voltar para Container

Se preferir voltar a usar containers (após testar localmente):

```bash
# Remover Selenium das dependências ou usar apenas coletores que não precisam
# Edit requirements.txt e remover: selenium, webdriver-manager

# Reconstruir imagem
docker compose build

# Executar
docker compose up -d
```

## 💡 Dica: Script de ativação rápida

Crie um alias no seu `.bashrc` ou `.zshrc`:

```bash
echo 'alias dje="cd /home/rodgb/personal/radarjud/dje-monitor && source venv/bin/activate"' >> ~/.bashrc
source ~/.bashrc

# Agora você pode usar:
dje
python test_comunica.py
```
