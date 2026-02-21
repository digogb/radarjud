# DJE Monitor - Project Context

## Visão Geral
**DJE Monitor** é um sistema web completo para monitorar automaticamente o Diário da Justiça Eletrônico (DJe) via API DJEN. O sistema permite cadastrar partes adversas (pessoas físicas ou jurídicas) por nome e tribunal, consulta periodicamente a API DJEN em busca de novas publicações, gera alertas quando há novidades e exibe tudo em uma interface React. Além da busca textual exata, o sistema conta com **busca semântica** via embeddings vetoriais (Qdrant + Nomic), permitindo encontrar publicações por contexto jurídico sem necessidade de correspondência exata de palavras.

---

## Principais Funcionalidades

1. **Busca no DJe (ad hoc)**
   - Consulta à API DJEN por nome da parte ou número do processo (CNJ).
   - Filtro opcional por tribunal.
   - Exibição dos polos ativo/passivo, órgão, tipo de comunicação e texto completo.
   - Drawer lateral com histórico de publicações de um processo.

2. **Busca Semântica**
   - Toggle "Busca Exata / Busca Semântica" na página de busca.
   - Modelo `nomic-ai/nomic-embed-text-v1.5` (8192 tokens, Matryoshka 256 dims).
   - Indexação automática de publicações no Qdrant após cada save.
   - Busca em publicações individuais ou por processo (histórico concatenado).
   - Filtros híbridos: semântica + tribunal + pessoa_id.
   - Cards de resultado com barra de score colorida (verde/amarelo/vermelho).
   - Reindexação em massa via `POST /api/v1/search/reindex` ou script CLI.

3. **Monitoramento Automático de Pessoas**
   - Cadastro de partes por nome (e CPF/CNPJ opcional), com filtro de tribunal e intervalo de verificação (6h, 12h, 24h, 48h).
   - **First check** ao cadastrar: puxa publicações existentes sem gerar alertas (baseline).
   - Verificações periódicas paralelas via workers Dramatiq.
   - Deduplicação por `hash_unico` — cada publicação é salva apenas uma vez.
   - Suporte a data de expiração: monitoramentos podem ter prazo (ex: 5 anos após data do processo).
   - Importação em massa via planilha Excel (`.xlsx`) com dry-run para validação prévia.

4. **Sistema de Alertas**
   - Alerta gerado para cada nova publicação encontrada.
   - Badge de não-lidos na interface; marcação individual ou em massa como lido.
   - Suporte a `tipo` de alerta: `NOVA_PUBLICACAO` (padrão) e `OPORTUNIDADE_CREDITO`.
   - Endpoint `/api/v1/alertas/nao-lidos/count` aceita filtro por `tipo`.

5. **Oportunidades de Crédito**
   - Varredura automática (a cada ciclo de sync) e sob demanda das publicações monitoradas em busca de sinais de recebimento de valores.
   - Padrões detectados via `ilike` no `texto_completo`: mandado de levantamento, alvará de levantamento/pagamento, expedição de precatório, precatório.
   - Janela de varredura automática: últimos 7 dias (`criado_em`). Janela de exibição na tela: últimos 30 dias (configurável até 365).
   - Alertas especiais `OPORTUNIDADE_CREDITO` com deduplicação por `publicacao_id`.
   - Actor Dramatiq `varrer_oportunidades_task` (fila `manutencao`) chamado em cada ciclo do scheduler.
   - Página dedicada **Oportunidades** com filtros, cards de resultado e drawer lateral com texto completo.

6. **Interface Web (React SPA)**
   - Todas as páginas têm ícone colorido no título (padrão visual unificado).
   - **Dashboard**: resumo estatístico (publicações, alertas não lidos, última sync).
   - **Busca**: busca ad hoc ou semântica com resultado em cards e drawer de detalhe. Aceita parâmetros via `location.state` (mesma aba) ou query string `?nome=&tribunal=` (nova aba).
   - **Monitorados**: lista de pessoas monitoradas com filtro, expansão de publicações e navegação integrada à Busca.
   - **Oportunidades**: publicações agrupadas por processo; filtros dinâmicos de nome e número de processo; drawer lateral com lista de publicações em accordion; botão "Varrer agora".
   - Navegação cruzada: Monitorados → Busca (mesma aba, router state); Oportunidades → Busca (nova aba, query params).

6. **Agendamento em Dois Níveis**
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
│   │   ├── embedding_service.py    # Embeddings semânticos (Nomic + Qdrant)
│   │   └── import_pessoas.py       # Importação de planilha Excel
│   ├── storage/
│   │   ├── models.py               # SQLAlchemy ORM (PostgreSQL) + to_dict()
│   │   └── repository.py           # CRUD, queries e batch para backfill
│   ├── extractors/                 # PDF/OCR (legado)
│   ├── matchers/                   # Matcher por CPF (legado)
│   └── notifiers/                  # Telegram / Email
├── web/                            # Frontend React + Vite + TypeScript
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Busca.tsx           # Busca exata + semântica com drawer de detalhe
│   │   │   ├── Monitorados.tsx     # Gestão de pessoas monitoradas
│   │   │   ├── Oportunidades.tsx   # Oportunidades de crédito detectadas
│   │   │   └── Dashboard.tsx       # Painel de resumo
│   │   └── services/api.ts         # Client HTTP + semanticApi + oportunidadesApi
│   └── nginx.conf
├── scripts/
│   └── backfill_embeddings.py      # CLI para reindexar publicações no Qdrant
├── tests/
│   ├── test_embedding_service.py   # Testes unitários + integração (semântica)
│   └── ...
├── docker-compose.yml              # 6 serviços: postgres, redis, qdrant, api, worker, web
├── Dockerfile
└── .env.example
```

### Containers (docker-compose)

| Serviço | Imagem / Build | Porta | Função |
|---|---|---|---|
| `postgres` | postgres:16-alpine | 5432 | Banco de dados principal |
| `redis` | redis:7-alpine | 6379 | Broker de filas Dramatiq |
| `qdrant` | qdrant/qdrant:v1.9.7 | 6333 | Vector store para busca semântica |
| `api` | `dje-monitor-backend:latest` (build local) | 8000 | FastAPI + APScheduler |
| `worker` | `dje-monitor-backend:latest` (imagem compartilhada com api) | — | Dramatiq (1 processo, 2 threads) |
| `web` | build local (node:20-alpine + nginx) | 80 | React SPA servida via nginx |

### Banco de Dados (PostgreSQL)

| Tabela | Descrição |
|---|---|
| `pessoas_monitoradas` | Partes cadastradas para monitoramento |
| `publicacoes_monitoradas` | Publicações encontradas (deduplicadas por `hash_unico`) |
| `alertas` | Alertas de publicações; campo `tipo` distingue `NOVA_PUBLICACAO` de `OPORTUNIDADE_CREDITO` |
| `cpfs_monitorados` | Legado: monitoramento por CPF via PDF |
| `diarios_processados` | Legado: controle de PDFs baixados |
| `ocorrencias` | Legado: matches de CPF em PDFs |

### Qdrant (Vector Store)

| Collection | Conteúdo | Dimensões | Índices de payload |
|---|---|---|---|
| `publicacoes` | Uma publicação por vetor | 256 (Matryoshka) | tribunal, pessoa_id, numero_processo, data_disponibilizacao |
| `processos` | Histórico concatenado de um processo | 256 (Matryoshka) | tribunal, numero_processo |

### Filas Dramatiq (Redis)

| Fila | Actor | Função |
|---|---|---|
| `scheduler` | `agendar_verificacoes_task` | Seleciona pessoas elegíveis e enfileira verificações |
| `verificacao` | `verificar_pessoa_task` | Verifica uma pessoa específica no DJe |
| `verificacao` | `first_check_task` | First check ao cadastrar (sem gerar alertas) |
| `manutencao` | `desativar_expirados_task` | Desativa monitoramentos expirados |
| `manutencao` | `varrer_oportunidades_task` | Detecta padrões de crédito e gera alertas OPORTUNIDADE_CREDITO |
| `indexacao` | `indexar_publicacao_task` | Vetoriza e indexa publicação no Qdrant |
| `indexacao` | `indexar_processo_task` | Vetoriza histórico de processo no Qdrant |
| `indexacao` | `reindexar_tudo_task` | Backfill completo de todas as publicações |

### Fluxo de Indexação Semântica
```
Nova Publicação salva (monitor_service.py)
  └── indexar_publicacao_task.send(pub_id, pub.to_dict())
        └── Worker fila "indexacao"
              ├── ensure_collections()        — cria collection no Qdrant se não existir
              ├── build_publicacao_text()     — concatena texto + polos + órgão + processo
              ├── encode("search_document: ...") — Nomic → vetor 256 dims
              └── qdrant.upsert(id, vector, payload)
```

### Fluxo de Busca Semântica
```
Usuário: "execução fiscal dívida tributária"
  └── GET /api/v1/search/semantic?q=...&tribunal=TJCE&tipo=publicacoes
        ├── encode("search_query: ...")     — mesmo modelo, prefixo diferente
        ├── qdrant.search(vector, filter=tribunal, top_k=20, score_threshold=0.35)
        └── Retorna publicações rankeadas por similaridade de cosseno
```

### Fluxo de Agendamento
```
APScheduler (API) — a cada DJE_MONITOR_INTERVAL_MINUTES (padrão: 30 min)
  └── agendar_verificacoes_task.send()
        └── SELECT pessoas WHERE ativo=True AND proximo_check <= NOW()
              ORDER BY proximo_check ASC LIMIT 500
        └── verificar_pessoa_task.send(pessoa_id) [por pessoa]
              └── Busca API DJEN → dedup por hash_unico → salva publicação → gera alerta
              └── indexar_publicacao_task.send()  ← indexação semântica automática
              └── atualiza ultimo_check e proximo_check = NOW() + intervalo_horas
        └── varrer_oportunidades_task.send()  ← roda a cada ciclo (independente de pessoas)
              └── buscar_oportunidades(dias=7) → ilike patterns no texto_completo
              └── registrar_alerta(tipo=OPORTUNIDADE_CREDITO) se ainda não alertado
```

---

## Tecnologias

**Backend**
- Python 3.10+ | FastAPI | SQLAlchemy 2.x | Alembic-less (auto DDL no startup)
- Dramatiq + Redis (fila de tarefas assíncronas)
- APScheduler (agendamento interno da API)
- httpx | pydantic | openpyxl
- sentence-transformers (`nomic-ai/nomic-embed-text-v1.5`) — embeddings semânticos
- qdrant-client — interface com o vector store

**Frontend**
- React 18 + TypeScript + Vite
- React Router v6
- Lucide Icons | CSS customizado (sem framework de UI)

**Infraestrutura**
- PostgreSQL 16 | Redis 7 | Qdrant v1.9.7
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
| `DJE_QDRANT_URL` | `http://qdrant:6333` | URL do Qdrant |
| `DJE_EMBEDDING_MODEL` | `nomic-ai/nomic-embed-text-v1.5` | Modelo de embedding |
| `DJE_EMBEDDING_DIMS` | `256` | Dimensões Matryoshka (256, 512 ou 768) |
| `DJE_SEMANTIC_SCORE_THRESHOLD` | `0.35` | Score mínimo de similaridade |
| `DJE_SEMANTIC_MAX_RESULTS` | `20` | Máximo de resultados semânticos |

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
# Qdrant:  http://localhost:6333/dashboard
```

### Backfill de Publicações Existentes
```bash
# Indexar publicações já salvas no Qdrant (rodar após primeiro deploy)
docker-compose exec worker python /app/scripts/backfill_embeddings.py

# Ou via endpoint (enfileira como task Dramatiq):
curl -X POST http://localhost:8000/api/v1/search/reindex
```

### Desenvolvimento Local (sem Docker)
```bash
# Backend
pip install -r requirements.txt
export DJE_DATABASE_URL="postgresql://..."
export DJE_REDIS_URL="redis://localhost:6379/0"
export DJE_QDRANT_URL="http://localhost:6333"
uvicorn api:app --reload --app-dir src

# Worker (terminal separado)
cd src && python -m dramatiq tasks --processes 1 --threads 4

# Frontend
cd web && npm install && npm run dev

# Qdrant local (Docker)
docker run -p 6333:6333 qdrant/qdrant:v1.9.7
```

### Testes
```bash
# Testes unitários (sem dependências externas)
DJE_TEST_DATABASE_URL="postgresql://..." pytest tests/

# Testes de integração semântica (requerem Qdrant rodando)
DJE_TEST_DATABASE_URL="postgresql://..." pytest tests/ -m integration
```

---

## Principais Endpoints da API

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/v1/search?nome=&tribunal=` | Busca ad hoc no DJEN |
| `GET` | `/api/v1/search/semantic?q=&tribunal=&tipo=` | Busca semântica (publicacoes/processos) |
| `GET` | `/api/v1/search/semantic/status` | Status do Qdrant e contadores |
| `POST` | `/api/v1/search/reindex` | Dispara reindexação completa no Qdrant |
| `GET` | `/api/v1/pessoas-monitoradas` | Lista pessoas monitoradas |
| `POST` | `/api/v1/pessoas-monitoradas` | Cadastra pessoa (dispara first_check) |
| `DELETE` | `/api/v1/pessoas-monitoradas/{id}` | Remove monitoramento (soft delete) |
| `GET` | `/api/v1/pessoas-monitoradas/{id}/publicacoes` | Publicações de uma pessoa |
| `GET` | `/api/v1/alertas` | Lista alertas com filtros |
| `POST` | `/api/v1/alertas/marcar-lidos` | Marca alertas como lidos |
| `GET` | `/api/v1/oportunidades?dias=30&limit=50` | Lista publicações com padrões de crédito detectados |
| `POST` | `/api/v1/oportunidades/varrer` | Dispara varredura imediata de oportunidades |
| `POST` | `/api/v1/importar-planilha` | Import Excel de partes adversas |
| `POST` | `/api/sync/forcar` | Força ciclo de verificação imediato |
| `GET` | `/api/sync/status` | Status do scheduler e filas Redis |
| `GET` | `/api/dashboard/resumo` | Estatísticas para o dashboard |
