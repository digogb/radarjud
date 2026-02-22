# Plano de Parametrização — DJE Monitor

## Visão Geral

Documentação técnica de todas as funcionalidades implementadas na feature de parametrização de oportunidades do DJE Monitor.

---

## 1. Arquitetura Geral

```
dje-monitor/
├── src/
│   ├── api.py                    # FastAPI — endpoints REST
│   ├── services/
│   │   ├── embedding_service.py  # Geração de embeddings (sentence-transformers)
│   │   └── oportunidades_service.py  # Lógica de negócio de oportunidades
│   └── storage/
│       ├── models.py             # SQLAlchemy ORM models
│       └── repository.py        # Queries e lógica de dados
└── web/
    └── src/
        ├── pages/
        │   ├── Oportunidades.tsx     # Lista de oportunidades por pessoa
        │   └── Parametrizacao.tsx    # CRUD de padrões positivos e negativos
        └── services/
            └── api.ts                # Client HTTP para o backend
```

### Stack
- **Backend**: Python + FastAPI + SQLAlchemy + PostgreSQL
- **Frontend**: React + TypeScript
- **Busca semântica**: sentence-transformers (`neuralmind/bert-base-portuguese-cased`) + Qdrant
- **Deploy**: Docker Compose

---

## 2. Tabela `padroes_oportunidade`

### Modelo

```python
class PadraoOportunidade(Base):
    __tablename__ = "padroes_oportunidade"
    id        = Column(Integer, primary_key=True)
    nome      = Column(String(200), nullable=False)
    expressao = Column(String(500), nullable=False)
    ativo     = Column(Boolean, default=True)
    ordem     = Column(Integer)
    tipo      = Column(String(20), nullable=False, default='positivo')
```

### Migrações aplicadas manualmente (ALTER TABLE)

```sql
ALTER TABLE padroes_oportunidade ADD COLUMN ordem INTEGER;
ALTER TABLE padroes_oportunidade ADD COLUMN tipo VARCHAR(20) NOT NULL DEFAULT 'positivo';
```

> **Atenção**: `SQLAlchemy create_all()` NÃO altera tabelas existentes. Colunas novas exigem `ALTER TABLE` manual no banco.

### Valores do campo `tipo`

| Valor | Descrição |
|-------|-----------|
| `'positivo'` | Palavra/frase que indica uma oportunidade de crédito |
| `'negativo'` | Palavra/frase que invalida uma oportunidade (ex: anulação posterior) |

---

## 3. Padrões Padrão (Seeds)

Inseridos automaticamente na primeira execução, se a tabela estiver vazia para cada tipo.

### Padrões Positivos

| Nome | Expressão |
|------|-----------|
| Expedição de Precatório | expedição de precatório |
| Alvará | alvará |
| Precatório Alimentar | precatório alimentar |
| RPV | rpv |
| Requisição de Pequeno Valor | requisição de pequeno valor |
| Pagamento Homologado | homologação do cálculo |

### Padrões Negativos

| Nome | Expressão |
|------|-----------|
| Anulação | anulação |
| Cassação | cassação |
| Suspensão | suspensão |
| Revogação | revogação |
| Reforma | reformado |
| Rescisão | rescisão |
| Extinção | extinção |

> Os padrões negativos devem ser palavras ou frases em português completo (não usar stems como "anulad").

---

## 4. Endpoints da API

### Padrões de Oportunidade

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/v1/padroes-oportunidade` | Lista todos os padrões (ordenados por `ordem`) |
| POST | `/api/v1/padroes-oportunidade` | Cria novo padrão |
| PUT | `/api/v1/padroes-oportunidade/{id}` | Atualiza padrão |
| DELETE | `/api/v1/padroes-oportunidade/{id}` | Remove padrão |
| POST | `/api/v1/padroes-oportunidade/reordenar` | Salva nova ordem de IDs |

> **IMPORTANTE (FastAPI route ordering)**: A rota `/reordenar` DEVE ser declarada ANTES da rota `/{padrao_id}` no código. Caso contrário, FastAPI interpreta a string literal "reordenar" como valor do parâmetro `padrao_id`, causando erro 405.

### Oportunidades

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/v1/oportunidades` | Lista oportunidades com agrupamento por processo |

---

## 5. Lógica de Busca de Oportunidades

### Fluxo em `repository.py → buscar_oportunidades()`

1. Carrega **todos** os padrões ativos do banco (`ativo=True`)
2. Separa em dois grupos:
   - `padroes_pos`: tipo = `'positivo'`
   - `padroes_neg`: tipo = `'negativo'`
3. **Busca positiva**: filtra publicações cujo `texto_completo` contenha qualquer padrão positivo (ILIKE `%expressao%`)
4. **Filtro negativo** (pós-processamento):
   - Para cada grupo único `(pessoa_id, numero_processo)` com publicações positivas:
     - Encontra a data mais recente da publicação positiva no processo
     - Busca se existe alguma publicação com data POSTERIOR a essa, no mesmo processo, contendo qualquer padrão negativo
   - Se encontrar → marca o processo como invalidado
5. Remove os processos invalidados do resultado final

```python
# Exemplo simplificado do filtro negativo
filtros_neg = [
    PublicacaoMonitorada.texto_completo.ilike(f'%{p.expressao}%')
    for p in padroes_neg
]

for (pessoa_id, numero_processo) in processos_unicos:
    max_data = max(datas do processo)
    pub_neg = session.query(...).filter(
        numero_processo == numero_processo,
        pessoa_id == pessoa_id,
        data_disponibilizacao > max_data,
        or_(*filtros_neg)
    ).first()
    if pub_neg:
        processos_invalidados.add((pessoa_id, numero_processo))
```

### Por que o filtro negativo é necessário?

A busca semântica (reranking com Qdrant) avalia **cada publicação em isolamento**. Ela não tem consciência de que uma publicação mais recente no mesmo processo pode ter anulado a oportunidade. O filtro negativo resolve isso como pós-processamento no banco.

---

## 6. Busca Semântica (Reranking)

- **Modelo**: `neuralmind/bert-base-portuguese-cased` (sentence-transformers)
- **Collection Qdrant**: `publicacoes` (variável `COLLECTION_PUBLICACOES`)
- **Quando é usada**: Quando o usuário ativa o filtro "Busca Semântica" na tela de Oportunidades
- **O que faz**: Reordena os resultados por similaridade semântica com a query do usuário

### Logs esperados na inicialização

```
# HEAD requests ao HuggingFace = validação de cache (não é download)
GET https://huggingface.co/.../config.json → 200

# "Batches" aparecem quando embedding_service.encode() é chamado (por requisição)
Batches: 100%|████| 1/1 [00:00<00:00, ...]
```

---

## 7. Frontend

### Página Oportunidades (`Oportunidades.tsx`)

- Exibe resultados agrupados por pessoa e processo
- **Ordenação** (canto superior direito acima da lista):
  - Data (mais recente primeiro) — padrão
  - Data (mais antiga primeiro)
  - Nome (A → Z)
  - Mais publicações
- Filtro adicional de busca semântica (opcional)

### Página Parametrização (`Parametrizacao.tsx`)

Layout em **abas** dentro de um único card:

```
┌─────────────────────────────────────────────────────┐
│  ● Padrões Positivos (N)  │  Padrões Negativos (N)  │
│  ─────────────────────    │  [Desmarcar todos][Add]  │
│  [Drag] Nome   Expr Ativo │                          │
│  ...                      │                          │
└─────────────────────────────────────────────────────┘
```

**Funcionalidades por aba:**
- Drag-and-drop para reordenar (apenas dentro do mesmo tipo)
- Toggle de ativo/inativo por padrão
- **Marcar todos / Desmarcar todos**: ativa ou desativa todos os padrões da aba com `Promise.all` (chamadas paralelas)
- Formulário de adição (aparece ao clicar em "Adicionar")
- Exclusão individual

**Estados relevantes:**
```typescript
const [abaAtiva, setAbaAtiva] = useState<Tipo>('positivo')
const [togglando, setTogglando] = useState(false)
const [mostrarForm, setMostrarForm] = useState<Tipo | null>(null)
```

**Reordenação:**
- Ao fazer drag-and-drop, chama `/reordenar` apenas com os IDs do tipo da aba ativa
- Não mistura IDs de positivos e negativos

---

## 8. Considerações de Deploy

### Backend (FastAPI)
- Volume mount `./src:/app/src` → mudanças em Python são aplicadas **sem rebuild**
- Reiniciar container após mudanças em `models.py` que precisem de migração

### Frontend (React)
- Build estático gerado na **imagem Docker** — mudanças em `.tsx` exigem rebuild:
  ```bash
  docker compose build --no-cache web
  docker compose up -d web
  ```

### Banco de dados
- Migrações não são automáticas — usar `ALTER TABLE` manualmente para novas colunas
- Seeds são inseridas automaticamente na inicialização se não existirem padrões

---

## 9. Problemas Resolvidos

| Problema | Causa | Solução |
|----------|-------|---------|
| 405 em POST `/reordenar` | FastAPI capturava "reordenar" como `{padrao_id}` | Mover rota `/reordenar` antes de `/{padrao_id}` |
| 502 em GET `/padroes-oportunidade` | Coluna `ordem` não existia na tabela | `ALTER TABLE ... ADD COLUMN ordem INTEGER` |
| Mudanças frontend não refletidas | Container usa build de imagem, não volume | `docker compose build --no-cache web` |
| Falso positivo de oportunidade | Busca semântica não detecta anulação posterior | Implementar filtro negativo pós-busca |
| Expressões truncadas ("anulad") | Seeds usando stems em vez de palavras completas | Atualizar seeds e registros existentes no BD |
