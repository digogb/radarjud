from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Any
from datetime import date
import logging
import sys
import os

# Adiciona diretório src ao path para imports funcionarem se rodar direto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from collectors.djen_collector import DJENCollector

# Configuração de Logs básica
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("api")

app = FastAPI(title="DJE Monitor API", version="1.0.0")

# CORS (Permitir frontend react local)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção deve ser restritivo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instância global do coletor (para reuso de sessão HTTP se mantida)
# Mas o coletor atual cria cliente novo a cada request se não for persistente
collector = DJENCollector(tribunal="TJCE") # Default, mas a busca por nome é nacional no DJEN

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "dje-monitor-api"}

@app.get("/api/v1/search")
async def search_name(
    nome: str = Query(..., min_length=3, description="Nome da parte a ser buscada"),
    tribunal: Optional[str] = Query(None, description="Filtro opcional de tribunal")
):
    """
    Busca comunicações no DJEN pelo nome da parte.
    """
    logger.info(f"Recebida busca por nome: {nome}")
    
    try:
        # A busca por nome no DJEN ignora datas no request atual, 
        # mas a assinatura do método exige datas. Passamos hoje como placeholder.
        # O coletor ignora as datas na chamada à API, conforme nossa alteração recente.
        hoje = date.today()
        
        # Se um tribunal específico foi pedido, poderíamos filtrar no pós-processamento,
        # mas por enquanto retornamos tudo que o DJEN mandar.
        if tribunal:
            # TODO: Implementar filtro de tribunal se necessário
            pass

        # Executa a busca síncrona (httpx)
        resultados = collector.buscar_por_nome(nome, hoje, hoje)
        
        return {
            "count": len(resultados),
            "results": resultados
        }
        
    except Exception as e:
        logger.error(f"Erro na busca API: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Dashboard Mocks ---
@app.get("/api/dashboard/resumo")
def dashboard_resumo():
    return {
        "totalProcessos": 0,
        "processosMonitorados": 0,
        "alteracoesNaoVistas": 0,
        "ultimaSync": None
    }

@app.get("/api/dashboard/alteracoes")
def dashboard_alteracoes(limit: int = 10):
    return []

@app.get("/api/dashboard/estatisticas/tribunais")
def dashboard_stats_tribunais():
    return []
