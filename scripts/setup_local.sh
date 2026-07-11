#!/bin/bash
# Script para configurar ambiente local do DJE Monitor

set -e  # Parar em caso de erro

echo "=== DJE Monitor - Setup Local ==="
echo ""

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Função para printar com cor
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Verificar se está no diretório correto
if [ ! -f "requirements.txt" ]; then
    print_error "Execute este script do diretório dje-monitor/"
    exit 1
fi

echo "1. Verificando pré-requisitos..."
echo ""

# Verificar Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_success "Python encontrado: $PYTHON_VERSION"
else
    print_error "Python 3 não encontrado. Instale com: sudo apt install python3"
    exit 1
fi

# Verificar pip
if command -v pip3 &> /dev/null || python3 -m pip --version &> /dev/null; then
    print_success "pip encontrado"
else
    print_warning "pip não encontrado. Tentando instalar..."
    sudo apt update
    sudo apt install -y python3-pip
fi

# Verificar python3-venv
if python3 -m venv --help &> /dev/null 2>&1; then
    print_success "python3-venv disponível"
else
    print_warning "python3-venv não encontrado. Instalando..."
    sudo apt install -y python3.12-venv || sudo apt install -y python3-venv
fi

# Verificar Chrome
if command -v google-chrome &> /dev/null; then
    CHROME_VERSION=$(google-chrome --version)
    print_success "Chrome encontrado: $CHROME_VERSION"
else
    print_warning "Chrome não encontrado. Instalando..."
    wget -q -O /tmp/google-chrome-key.pub https://dl-ssl.google.com/linux/linux_signing_key.pub
    sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/google-chrome.gpg /tmp/google-chrome-key.pub
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
    sudo apt update
    sudo apt install -y google-chrome-stable
    rm /tmp/google-chrome-key.pub
    print_success "Chrome instalado"
fi

# Verificar Tesseract
if command -v tesseract &> /dev/null; then
    TESSERACT_VERSION=$(tesseract --version 2>&1 | head -1)
    print_success "Tesseract encontrado: $TESSERACT_VERSION"
else
    print_warning "Tesseract não encontrado. Instalando..."
    sudo apt install -y tesseract-ocr tesseract-ocr-por
    print_success "Tesseract instalado"
fi

echo ""
echo "2. Criando ambiente virtual..."
echo ""

# Remover venv antigo se existir
if [ -d "venv" ]; then
    print_warning "Ambiente virtual existente encontrado. Removendo..."
    rm -rf venv
fi

# Criar venv
python3 -m venv venv
print_success "Ambiente virtual criado"

# Ativar venv e instalar dependências
echo ""
echo "3. Instalando dependências Python..."
echo ""

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

print_success "Dependências instaladas"

echo ""
echo "4. Verificando instalação..."
echo ""

# Testar imports
python3 -c "import selenium; print('Selenium OK')"
python3 -c "import httpx; print('httpx OK')"
python3 -c "import pytesseract; print('pytesseract OK')"

print_success "Todos os módulos Python carregados com sucesso"

echo ""
echo "=== Setup concluído! ==="
echo ""
echo "Para usar o ambiente:"
echo "  source venv/bin/activate"
echo ""
echo "Comandos disponíveis:"
echo "  python test_comunica.py              # Testar ComunicaCollector"
echo "  cd src && python main.py executar    # Executar monitoramento"
echo "  cd src && python main.py scheduler   # Modo contínuo"
echo ""
echo "Consulte SETUP_LOCAL.md para mais informações."
echo ""
