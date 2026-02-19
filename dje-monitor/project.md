# DJE Monitor - Project Context

## Visão Geral
**DJE Monitor** é um sistema web completo para monitorar automaticamente o Diário da Justiça Eletrônico (DJe) via API DJEN. O sistema permite cadastrar partes adversas (pessoas físicas ou jurídicas) por nome e tribunal, consulta periodicamente a API DJEN em busca de novas publicações, gera alertas quando há novidades e exibe tudo em uma interface React.

---

## Principais Funcionalidades

1. **Busca no DJe (ad hoc)**
   - Consulta à API DJEN por nome da parte ou número do processo (CNJ).
   - Filtro opcional por tribunal.
   - Exibição dos polos ativo/passivo, órgão, tipo de comunicação e texto completo.
   - Drawer lateral com histórico de publicações de um processo.

2. **Monitoramento Automático de Pessoas**
   - Cadastro de partes por nome (e CPF/CNPJ opcional), com filtro de tribunal e intervalo de verificação (6h, 12h, 24h, 48h).
   - **First check** ao cadastrar: puxa publicações existentes sem gerar alertas (baseline).
   - Verificações periódicas paralelas via workers Dramatiq.
   - Deduplicação por `hash_unico` — cada publicação é salva apenas uma vez.
   - Suporte a data de expiração: monitoramentos podem ter prazo (ex: 5 anos após data do processo).
   - Importação em massa via planilha Excel (`.xlsx`) com dry-run para validação prévia.

3. **Sistema de Alertas**
   - Alerta gerado para cada nova publicação encontrada.
   - Badge de não-lidos na interface; marcação individual ou em massa como lido.

4. **Interface Web (React SPA)**
   - **Dashboard**: resumo estatístico (publicações, alertas não lidos, última sync).
   - **Busca**: busca ad hoc com resultado em cards e drawer de detalhe.
   - **Monitorados**: lista de pessoas monitoradas com filtro, expansão de publicações e navegação integrada à Busca.
   - Navegação cruzada: de uma publicação no Monitorados → Busca pré-preenchida com nome ou número do processo.

5. **Agendamento em Dois Níveis**
   - APScheduler na API enfileira `agendar_verificacoes_task` a cada N minutos.
   - Worker Dramatiq processa as pessoas elegíveis (`proximo_check <= agora`) em paralelo (8 threads).

---

## Arquitetura

### Estrutura de Diretórios
```
dje-monitor/
├── src/
│   ├── api.py                      # FastAPI: endpoints REST + APScheduler
│   ├── tasks.py                    # Dramatiq actors (workers assíncronos)
│   ├── config.py                   # Config via env vars (requer DJE_DATABASE_URL)
│   ├── collectors/
│   │   ├── djen_collector.py       # Integração com API DJEN (busca por nome/processo)
│   │   ├── comunica_collector.py
│   │   └── esaj_collector.py
│   ├── services/
│   │   ├── monitor_service.py      # Lógica de verificação e deduplicação
│   │   └── import_pessoas.py       # Importação de planilha Excel
│   ├── storage/
│   │   ├── models.py               # SQLAlchemy ORM (PostgreSQL)
│   │   └── repository.py           # CRUD e queries do banco
│   ├── extractors/                 # PDF/OCR (legado)
│   ├── matchers/                   # Matcher por CPF (legado)
│   └── notifiers/                  # Telegram / Email
├── web/                            # Frontend React + Vite + TypeScript
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Busca.tsx           # Busca ad hoc com drawer de detalhe
│   │   │   ├── Monitorados.tsx     # Gestão de pessoas monitoradas
│   │   │   └── Dashboard.tsx       # Painel de resumo
│   │   └── services/api.ts         # Client HTTP para a API
│   └── nginx.conf
├── tests/                          # pytest (requer DJE_TEST_DATABASE_URL)
├── docker-compose.yml              # 5 serviços: postgres, redis, api, worker, web
├── Dockerfile
└── .env.example
```

### Containers (docker-compose)

| Serviço | Imagem / Build | Porta | Função |
|---|---|---|---|
| `postgres` | postgres:16-alpine | 5432 | Banco de dados principal |
| `redis` | redis:7-alpine | 6379 | Broker de filas Dramatiq |
| `api` | build local | 8000 | FastAPI + APScheduler |
| `worker` | build local | — | Dramatiq (1 processo, 8 threads) |
| `web` | build local | 80 | React SPA servida via nginx |

### Banco de Dados (PostgreSQL)

| Tabela | Descrição |
|---|---|
| `pessoas_monitoradas` | Partes cadastradas para monitoramento |
| `publicacoes_monitoradas` | Publicações encontradas (deduplicadas por `hash_unico`) |
| `alertas` | Alertas de novas publicações (lido/não-lido) |
| `cpfs_monitorados` | Legado: monitoramento por CPF via PDF |
| `diarios_processados` | Legado: controle de PDFs baixados |
| `ocorrencias` | Legado: matches de CPF em PDFs |

### Filas Dramatiq (Redis)

| Fila | Actor | Função |
|---|---|---|
| `scheduler` | `agendar_verificacoes_task` | Seleciona pessoas elegíveis e enfileira verificações |
| `verificacao` | `verificar_pessoa_task` | Verifica uma pessoa específica no DJe |
| `verificacao` | `first_check_task` | First check ao cadastrar (sem gerar alertas) |
| `manutencao` | `desativar_expirados_task` | Desativa monitoramentos expirados |

### Fluxo de Agendamento
```
APScheduler (API) — a cada DJE_MONITOR_INTERVAL_MINUTES (padrão: 30 min)
  └── agendar_verificacoes_task.send()
        └── SELECT pessoas WHERE ativo=True AND proximo_check <= NOW()
              ORDER BY proximo_check ASC LIMIT 500
        └── verificar_pessoa_task.send(pessoa_id) [por pessoa]
              └── Busca API DJEN → dedup por hash_unico → salva publicação → gera alerta
              └── atualiza ultimo_check e proximo_check = NOW() + intervalo_horas
```

---

## Tecnologias

**Backend**
- Python 3.10+ | FastAPI | SQLAlchemy 2.x | Alembic-less (auto DDL no startup)
- Dramatiq + Redis (fila de tarefas assíncronas)
- APScheduler (agendamento interno da API)
- httpx | pydantic | openpyxl

**Frontend**
- React 18 + TypeScript + Vite
- React Router v6
- Lucide Icons | CSS customizado (sem framework de UI)

**Infraestrutura**
- PostgreSQL 16 | Redis 7
- Docker + Docker Compose
- nginx (serve o build do frontend)

---

## Configuração (Variáveis de Ambiente)

Definidas em `.env` (ver `.env.example`). As principais:

| Variável | Padrão | Descrição |
|---|---|---|
| `DJE_DATABASE_URL` | **obrigatório** | `postgresql://user:pass@host:5432/db` |
| `DJE_REDIS_URL` | `redis://localhost:6379/0` | URL do Redis |
| `DJE_MONITOR_HABILITADO` | `true` | Habilita o scheduler |
| `DJE_MONITOR_INTERVAL_MINUTES` | `30` | Frequência do ciclo de agendamento |
| `DJE_MONITOR_MAX_PAGINAS` | `10` | Máx. de páginas na busca DJEN por pessoa |
| `DJE_WORKER_THREADS` | `8` | Threads do worker Dramatiq |
| `DJE_RATE_LIMIT_PER_SEC` | `2.0` | Limite de requisições/seg à API DJEN |
| `DJE_TRIBUNAL` | `TJCE` | Tribunal padrão do collector |
| `DJE_TELEGRAM_BOT_TOKEN` | — | Bot Telegram para notificações |
| `DJE_TELEGRAM_CHAT_ID` | — | Chat ID do Telegram |
| `DJE_SMTP_HOST` / `_USER` / `_PASSWORD` | — | SMTP para notificações por email |

---

## Como Executar

### Docker (recomendado)
```bash
cp .env.example .env
# Editar .env com as credenciais reais

docker-compose up -d
# API:     http://localhost:8000
# Web:     http://localhost:80
# Docs:    http://localhost:8000/docs
```

### Desenvolvimento Local (sem Docker)
```bash
# Backend
pip install -r requirements.txt
export DJE_DATABASE_URL="postgresql://..."
export DJE_REDIS_URL="redis://localhost:6379/0"
uvicorn api:app --reload --app-dir src

# Worker (terminal separado)
cd src && python -m dramatiq tasks --processes 1 --threads 4

# Frontend
cd web && npm install && npm run dev
```

### Testes
```bash
# Os testes de banco requerem PostgreSQL configurado
DJE_TEST_DATABASE_URL="postgresql://..." pytest tests/
# Testes sem banco (config, collectors) rodam sem a env var
```

---

## Principais Endpoints da API

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/v1/search?nome=&tribunal=` | Busca ad hoc no DJEN |
| `GET` | `/api/v1/pessoas-monitoradas` | Lista pessoas monitoradas |
| `POST` | `/api/v1/pessoas-monitoradas` | Cadastra pessoa (dispara first_check) |
| `DELETE` | `/api/v1/pessoas-monitoradas/{id}` | Remove monitoramento (soft delete) |
| `GET` | `/api/v1/pessoas-monitoradas/{id}/publicacoes` | Publicações de uma pessoa |
| `GET` | `/api/v1/alertas` | Lista alertas com filtros |
| `POST` | `/api/v1/alertas/marcar-lidos` | Marca alertas como lidos |
| `POST` | `/api/v1/importar-planilha` | Import Excel de partes adversas |
| `POST` | `/api/sync/forcar` | Força ciclo de verificação imediato |
| `GET` | `/api/sync/status` | Status do scheduler e filas Redis |
| `GET` | `/api/dashboard/resumo` | Estatísticas para o dashboard |
