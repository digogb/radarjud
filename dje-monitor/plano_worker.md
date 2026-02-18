Plano: Escalar Monitoramento com Dramatiq + Redis
Contexto
O sistema DJe Monitor verifica publicações no DJe para pessoas monitoradas. Hoje o processamento é 100% sequencial: um loop em verificar_todas_pessoas() itera pessoa por pessoa, fazendo 1 chamada HTTP à API DJEN por pessoa (+ 1.5s de delay entre requests). Com 1000 pessoas, um ciclo leva ~140 minutos — excedendo o intervalo de 30 min do scheduler e causando sobreposição.

Problemas atuais:

Loop sequencial em monitor_service.verificar_todas_pessoas() — gargalo principal
API DJEN não suporta busca em batch (1 request por nome)
Delay de 1.5s por request (rate limiting)
DB pool padrão de 5 conexões (máx 15) — insuficiente para concorrência
Container dje-monitor (scheduler standalone) duplica trabalho com o scheduler embutido na API
Sem fila de tarefas — API bloqueia em operações pesadas (first_check, forçar sync)
Decisão do usuário:

Dramatiq + Redis como fila de tarefas
API + Worker dedicado (remover container scheduler standalone)
Arquitetura Alvo

┌─────────────┐     ┌───────────┐     ┌──────────────┐     ┌──────────┐
│  Frontend   │────▶│  API      │────▶│  Redis       │────▶│  Worker  │
│  (React)    │     │  (FastAPI)│     │  (Broker)    │     │ (Dramatiq│
│  :5173      │     │  :8000    │     │  :6379       │     │  N thrds)│
└─────────────┘     └─────┬─────┘     └──────────────┘     └────┬─────┘
                          │                                      │
                          └──────────┐  ┌────────────────────────┘
                                     ▼  ▼
                               ┌──────────────┐
                               │  PostgreSQL   │
                               │  :5432        │
                               └──────────────┘
API: Serve HTTP, enfileira tarefas, executa APScheduler leve (apenas dispara enqueue periódico)
Worker: Processa tarefas Dramatiq (verificar_pessoa, first_check, notificações)
Redis: Broker de mensagens Dramatiq + cache de rate limiting
Sem container dje-monitor: Removido, scheduler unificado na API
Alterações por arquivo
1. requirements.txt — novas dependências
Adicionar:

dramatiq[redis]>=1.15.0 — task queue + broker Redis
redis>=5.0.0 — cliente Redis (usado pelo Dramatiq e rate limiter)
apscheduler>=3.10.0 — já existe, manter
2. docker-compose.yml — nova arquitetura de containers
Adicionar container redis:


redis:
  image: redis:7-alpine
  container_name: dje-monitor-redis
  ports:
    - "6379:6379"
  restart: unless-stopped
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 5s
    timeout: 3s
    retries: 5
Substituir container dje-monitor por worker:


worker:
  build: .
  container_name: dje-monitor-worker
  entrypoint: []
  command: python -m dramatiq tasks --processes 1 --threads 8
  env_file: .env
  environment:
    - DJE_DATABASE_URL=postgresql://dje:dje_secret@postgres:5432/dje_monitor
    - DJE_REDIS_URL=redis://redis:6379/0
  depends_on:
    postgres: { condition: service_healthy }
    redis: { condition: service_healthy }
  restart: unless-stopped
Atualizar container api:

Adicionar DJE_REDIS_URL=redis://redis:6379/0
Adicionar dependência no redis
Remover --reload (dev only, performance)
3. config.py — novas configs
Adicionar:

redis_url: str — env DJE_REDIS_URL, default redis://localhost:6379/0
worker_threads: int — env DJE_WORKER_THREADS, default 8
rate_limit_per_second: float — env DJE_RATE_LIMIT_PER_SEC, default 2.0 (requests/sec global)
4. src/tasks.py — NOVO — definição das tarefas Dramatiq
Arquivo central que configura o broker e define os actors:


import dramatiq
from dramatiq.brokers.redis import RedisBroker

# Configurar broker Redis
broker = RedisBroker(url=config.redis_url)
dramatiq.set_broker(broker)

@dramatiq.actor(max_retries=3, min_backoff=10_000, max_backoff=60_000, queue_name="verificacao")
def verificar_pessoa_task(pessoa_id: int):
    """Verifica uma pessoa específica — executada pelo worker."""
    # Instancia repo + collector, chama lógica existente de MonitorService.verificar_pessoa()
    # Atualiza ultimo_check/proximo_check ao final

@dramatiq.actor(max_retries=1, queue_name="verificacao")
def first_check_task(pessoa_id: int, nome: str, tribunal_filtro: str | None = None):
    """First check assíncrono — executado pelo worker."""
    # Reutiliza MonitorService.first_check()

@dramatiq.actor(queue_name="scheduler")
def agendar_verificacoes_task():
    """Chamada pelo APScheduler da API. Consulta pessoas_para_verificar() e enfileira cada uma."""
    pessoas = repo.pessoas_para_verificar()
    for pessoa in pessoas:
        verificar_pessoa_task.send(pessoa.id)

@dramatiq.actor(queue_name="manutencao")
def desativar_expirados_task():
    """Manutenção periódica — desativa monitoramentos expirados."""
Filas separadas permitem priorização: verificacao (alta), scheduler (normal), manutencao (baixa).

5. src/services/monitor_service.py — refatorar para ser chamável pelo worker
Extrair a lógica de verificar_pessoa() para ser independente de instância:

Manter a classe MonitorService como está (para uso interno)
As tasks em tasks.py instanciam MonitorService por chamada (thread-safe, cada task cria sua própria sessão DB)
A mudança principal é:

Remover o loop sequencial de verificar_todas_pessoas() — agora a lógica de "para cada pessoa, enfileire" fica em agendar_verificacoes_task()
Manter verificar_pessoa() e first_check() como estão — são chamados pelas tasks
6. src/api.py — substituir BackgroundTasks por Dramatiq
Mudanças:

No startup, APScheduler agenda agendar_verificacoes_task.send() a cada N minutos (em vez de chamar verificar_todas_pessoas() direto)
POST /api/v1/pessoas-monitoradas → trocar background_tasks.add_task(monitor_service.first_check, ...) por first_check_task.send(pessoa.id, nome, tribunal_filtro)
POST /api/sync/forcar → trocar background_tasks.add_task(...) por agendar_verificacoes_task.send()
GET /api/sync/status → consultar Redis para obter info de filas (pendentes, em execução)
Importar e inicializar o broker Dramatiq
7. src/storage/repository.py — pool de conexões + otimizações
7a. Connection pool:


self.engine = create_engine(
    database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)
7b. Adicionar pessoas_para_verificar_batch():

Igual a pessoas_para_verificar() mas com ORDER BY proximo_check ASC e LIMIT N para processar em lotes
Faz SELECT ... FOR UPDATE SKIP LOCKED para evitar que workers concorrentes peguem a mesma pessoa (se necessário no futuro)
8. .env.example — documentar novas configs

# Redis (broker Dramatiq)
DJE_REDIS_URL=redis://redis:6379/0

# Worker
DJE_WORKER_THREADS=8
DJE_RATE_LIMIT_PER_SEC=2.0
9. Dockerfile — sem alterações estruturais
O mesmo Dockerfile serve para API e Worker (diferentes command/entrypoint no docker-compose).

Ordem de execução
requirements.txt — adicionar dramatiq, redis
config.py — novas configs (redis_url, worker_threads, rate_limit)
.env.example — documentar
docker-compose.yml — adicionar redis, substituir dje-monitor por worker, atualizar api
repository.py — pool de conexões, batch query
tasks.py — novo, definir actors Dramatiq
monitor_service.py — adaptar para ser thread-safe (sem estado compartilhado mutável)
api.py — trocar BackgroundTasks por .send(), ajustar scheduler
Verificação
docker compose up -d — subir todos os containers (postgres, redis, api, worker, web)
docker compose logs worker — verificar que o worker iniciou e conectou ao Redis
Criar uma pessoa via UI → verificar nos logs do worker que first_check_task executou
POST /api/sync/forcar → verificar que agendar_verificacoes_task enfileirou N tasks
Verificar nos logs do worker que as verificações rodam em paralelo (múltiplas threads)
Testar com 43 pessoas importadas — ciclo completo deve levar <1 min (8 threads × ~5s por pessoa)
GET /api/sync/status — deve mostrar info de filas