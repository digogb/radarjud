# Changelog — Últimas Alterações (fev/2026)

Documento descritivo das funcionalidades implementadas nas últimas sprints do DJE Monitor.

---

## 1. Resumo de Processo via IA (OpenAI)

**Commit:** `532743e` — 24/02/2026

### O que foi feito

Adicionamos a capacidade de gerar um **resumo jurídico estruturado** de qualquer processo diretamente na interface de Oportunidades, usando o modelo `gpt-4o-mini` da OpenAI.

### Como funciona

1. O usuário abre o drawer de detalhes de um processo na página Oportunidades.
2. Clica em **"Resumir processo"**.
3. O frontend chama `POST /api/v1/oportunidades/resumo` enviando o número do processo e a pessoa monitorada.
4. O backend (`resumo_service.py`) busca todas as publicações daquele processo no banco, monta um prompt jurídico e envia ao modelo.
5. A resposta é cacheada no Redis por 7 dias (chave versionada `v2` para invalidação limpa).
6. Na segunda chamada, o resultado é retornado instantaneamente do cache (indicado com ⚡ na UI).

### Saída do modelo

O modelo responde em Markdown estruturado com quatro seções:

- **Papel da Parte Monitorada** — se é autora/credora ou ré/devedora no processo
- **Linha do Tempo** — principais movimentações em ordem cronológica
- **Status Atual** — estado presente do processo
- **Valor Identificado** — valor em R$ se mencionado nas publicações

Ao final da resposta, o modelo emite um bloco de metadados parseável:

```
VEREDICTO: CREDITO_IDENTIFICADO | CREDITO_POSSIVEL | SEM_CREDITO
PAPEL: CREDOR | DEVEDOR | INDEFINIDO
VALOR: R$ X.XXX,XX | não identificado
```

### Exibição na UI (ResumoCard)

- Badges coloridos por veredicto: verde (`CREDITO_IDENTIFICADO`), amarelo (`CREDITO_POSSIVEL`), cinza (`SEM_CREDITO`)
- Badge de papel: azul (`CREDOR`) ou vermelho (`DEVEDOR`)
- Badge de valor quando identificado
- Texto do resumo renderizado via `react-markdown`

### Configuração

| Variável | Padrão | Descrição |
|---|---|---|
| `DJE_OPENAI_API_KEY` | — | Chave da API OpenAI (obrigatória para habilitar) |
| `DJE_OPENAI_MODEL` | `gpt-4o-mini` | Modelo a usar |

O recurso é **desabilitado automaticamente** se `DJE_OPENAI_API_KEY` não estiver definido (botão não aparece na UI).

### Arquivos alterados

- `src/services/resumo_service.py` — novo serviço (prompt, chamada OpenAI, parse, cache Redis)
- `src/api.py` — novo endpoint `POST /api/v1/oportunidades/resumo`
- `src/config.py` — novas vars `openai_api_key` e `openai_model`
- `src/collectors/djen_collector.py` — fallback regex para identificar polo quando a API DJEN não retorna
- `src/storage/repository.py` — `buscar_publicacoes_processo` com match por dígitos (`regexp_replace`) para tolerar variações de formatação do número CNJ
- `web/src/pages/Oportunidades.tsx` — botão "Resumir processo" + `ResumoCard`
- `web/src/services/api.ts` — `resumoApi.gerarResumo()`
- `requirements.txt` — adicionado `openai`
- `Dockerfile` — camadas estáveis (torch + sentence-transformers + modelo) antes do `COPY requirements.txt`, evitando re-download a cada mudança de dependências

---

## 2. Padrões Negativos e Parametrização Avançada

**Commit:** `10769d3` — 22/02/2026

### O que foi feito

Ampliamos o sistema de detecção de oportunidades com o conceito de **padrões negativos** — expressões que, quando presentes na publicação mais recente de um processo, fazem com que ele seja **excluído** da lista de oportunidades (ex: "improcedente", "extinto", "arquivado").

Além disso, a interface de parametrização foi reescrita com layout em abas separando positivos de negativos.

### Padrões positivos vs negativos

| Tipo | Função |
|---|---|
| **Positivo** | Indica possível recebimento de valores (ex: "alvará de levantamento", "expedição de precatório") |
| **Negativo** | Invalida/exclui o processo mesmo que tenha um padrão positivo anterior (ex: "pedido julgado improcedente", "processo extinto") |

A lógica é: primeiro a varredura encontra processos com padrões **positivos**; depois, filtra removendo aqueles cuja **publicação mais recente** contém algum padrão **negativo**.

### Novos campos na tabela `padroes_oportunidade`

| Campo | Tipo | Descrição |
|---|---|---|
| `tipo` | `varchar(20)` | `'positivo'` ou `'negativo'` |
| `ordem` | `integer` | Prioridade de aplicação (menor = maior prioridade) |

### Reordenamento

O endpoint `POST /api/v1/padroes-oportunidade/reordenar` recebe a nova sequência de IDs e persiste a ordem, que é refletida na interface e respeitada na varredura.

### Interface de Parametrização (`Parametrizacao.tsx`)

- **Duas abas**: "Padrões Positivos" e "Padrões Negativos"
- Por aba: lista de padrões com toggle ativo/inativo, setas de reordenamento, botão de exclusão com confirmação
- Botões **"Marcar todos"** e **"Desmarcar todos"** por aba (requisições paralelas com `Promise.all`)
- Formulário de criação de novo padrão (nome + expressão ILIKE)

### Ordenação da lista de Oportunidades

A página Oportunidades ganhou controle de **ordenação** da lista de processos:
- Por data mais recente
- Por nome da parte
- Por número de publicações

### Novos endpoints

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/v1/padroes-oportunidade` | Lista todos os padrões |
| `POST` | `/api/v1/padroes-oportunidade` | Cria novo padrão |
| `POST` | `/api/v1/padroes-oportunidade/reordenar` | Reordena padrões |
| `PUT` | `/api/v1/padroes-oportunidade/{id}` | Atualiza padrão |
| `DELETE` | `/api/v1/padroes-oportunidade/{id}` | Remove padrão |

> **Atenção técnica:** a rota `/reordenar` foi declarada **antes** de `/{padrao_id}` no FastAPI para evitar conflito de matching (405 Method Not Allowed).

### Arquivos alterados

- `src/storage/models.py` — modelo `PadraoOportunidade` com campos `tipo` e `ordem`
- `src/storage/repository.py` — queries de varredura com filtro negativo pós-busca
- `src/api.py` — CRUD completo de padrões + lógica de ordenação na listagem de oportunidades
- `web/src/pages/Parametrizacao.tsx` — reescrita com layout em abas
- `web/src/pages/Oportunidades.tsx` — controle de ordenação
- `web/src/App.tsx` — rota para `/parametrizacao`
- `web/src/services/api.ts` — `padroesApi`

---

## 3. Reranking Semântico de Oportunidades (Keywords + Vetores)

**Commit:** `166d310` — 21/02/2026

### O que foi feito

A detecção de oportunidades passou a combinar dois filtros em sequência para **reduzir falsos positivos**:

1. **Filtro por keyword** (ILIKE nos padrões positivos) — rápido, amplo
2. **Reranking semântico** (Qdrant) — confirma semanticamente se a publicação realmente é relevante

### Como funciona

O endpoint `GET /api/v1/oportunidades` aceita o parâmetro `semantico=true` (padrão). Quando habilitado:

1. O banco retorna os candidatos via ILIKE (padrões positivos)
2. Os IDs das publicações são enviados à função `rerank_oportunidades()` no `embedding_service.py`
3. O Qdrant calcula a similaridade de cada publicação em relação a um vetor de referência de "oportunidade de crédito"
4. Publicações com score abaixo de `0.45` são descartadas
5. O score semântico é retornado nos resultados para transparência

### Benefício

Evita que publicações que mencionam "levantamento" em contexto diferente (ex: levantamento de sigilo, levantamento topográfico) apareçam na lista de oportunidades.

### Arquivos alterados

- `src/services/embedding_service.py` — função `rerank_oportunidades()` + `index_publicacoes_batch()` para indexação em lote
- `src/api.py` — parâmetro `semantico` no endpoint de oportunidades
- `src/storage/repository.py` — suporte a batch queries

---

## 4. Página Oportunidades de Crédito

**Commit:** `d2d30ac` — 21/02/2026

### O que foi feito

Criamos a página dedicada **Oportunidades** no frontend — uma visão consolidada de todos os processos monitorados que apresentam sinais de recebimento de valores.

### Funcionalidades da página

- **Agrupamento por processo**: publicações do mesmo número CNJ são exibidas juntas em um card
- **Filtros dinâmicos**: por nome da parte e por número de processo
- **Drawer lateral**: ao clicar em um processo, abre um painel lateral com todas as publicações em accordion (expandível individualmente)
- **Botão "Varrer agora"**: dispara `POST /api/v1/oportunidades/varrer` para executar a varredura imediata sem aguardar o ciclo automático
- **Navegação cruzada**: link "Ver no histórico" abre a página Busca em nova aba com os parâmetros da pessoa e tribunal já preenchidos

### Varredura automática

A cada ciclo do scheduler (padrão: 30 min), após verificar as pessoas monitoradas, o actor `varrer_oportunidades_task` roda automaticamente e gera alertas do tipo `OPORTUNIDADE_CREDITO` para novos processos detectados (deduplicação por `publicacao_id`).

### Arquivos alterados

- `web/src/pages/Oportunidades.tsx` — novo (636 linhas na versão inicial)
- `src/api.py` — endpoints de oportunidades
- `src/storage/repository.py` — `buscar_oportunidades()` com agrupamento e filtros
- `src/tasks.py` — `varrer_oportunidades_task` integrado ao ciclo do scheduler

---

## 5. Fix: Limite de File Descriptors do Qdrant

**Commit:** `c8c053d` — 21/02/2026

### O que foi feito

O container do Qdrant atingia o limite padrão de file descriptors do sistema sob carga, causando erros de indexação silenciosos.

### Solução

Adicionadas configurações no `docker-compose.yml`:

```yaml
qdrant:
  ulimits:
    nofile:
      soft: 65536
      hard: 65536
```

---

## Resumo de Impacto

| Área | Antes | Depois |
|---|---|---|
| Oportunidades | Lista plana com ILIKE simples | Agrupada por processo, com reranking semântico e filtro negativo |
| Análise de processo | Manual (ler texto das publicações) | Resumo automático com IA: veredicto, papel e valor |
| Parametrização | Padrões hardcoded no código | CRUD via interface, com tipos positivo/negativo e reordenamento |
| Falsos positivos | Sem controle | Filtro negativo + reranking semântico (threshold 0.45) |
