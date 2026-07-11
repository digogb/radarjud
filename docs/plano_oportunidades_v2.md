# Plano: Melhoria do Pipeline de Oportunidades v2

Data: 2026-07-11 · Branch base: `fix/oportunidades-classificacao`
Origem: análise completa do pipeline (repository → varredura → rerank → classificação LLM → alertas → UI).

## Contexto

O pipeline atual funciona em 5 estágios:

```
ILIKE padrões positivos (90d, limit 500)          ← repository.buscar_oportunidades
  → filtro intra-pub negativo + filtro de polo
  → filtro "negativo posterior" por processo
  → rerank semântico Qdrant (threshold 0.45)
  → classificação LLM por (pessoa, processo)      ← fila classificacao, cache Redis 7d + DB
  → alertas (janela 7d, skip DEVEDOR)
  → UI: Oportunidades / Acompanhar / Descartados IA / Descartados usuário
```

A v1 (Plano_melhoria_oportunidade.md) resolveu a classificação credor/devedor. Esta v2 ataca
bugs residuais que geram **falsos negativos silenciosos** e **notificações erradas**, além de
melhorias de recall, custo e arquitetura.

---

## FASE 1 — Quick wins (bugs que afetam clientes hoje)

### 1.1 Padrões negativos genéricos matam sinais positivos fortes 🔴

**Problema:** os seeds negativos (`repository.py` `_PADROES_PADRAO_NEGATIVOS`) incluem
`"extinção"`, `"suspensão"`, `"rescisão"`. O filtro de "negativo posterior" invalida o
**processo inteiro** quando uma pub posterior contém o termo. Mas:

- **"extinção da execução pelo pagamento" (art. 924, II CPC) é o sinal MÁXIMO de crédito
  recebido/em recebimento** — hoje ele REMOVE o processo da lista.
- "suspensão" por acordo de parcelamento = recebimento futuro (positivo).
- "rescisão" casa por substring com "ação rescisória" (irrelevante).

**Solução:**
- Adicionar padrão **positivo**: `("Extinção pelo Pagamento", "extinção da execução pelo pagamento")`
  e variação `"extinta a execução pelo pagamento"`.
- Refinar negativos do seed: trocar `"extinção"` por expressões específicas que de fato
  encerram sem crédito (ex.: `"extinção sem resolução do mérito"`, `"improcedência"`).
  Remover `"suspensão"` e `"rescisão"` do seed ou torná-los mais específicos.
- **Migração de dados**: atualizar os padrões existentes nos 3 tenants do stage
  (seed só roda em tabela vazia). Script SQL idempotente em `scripts/migrations/`.
- Regra de precedência no filtro intra-pub: se o texto contém padrão positivo E negativo,
  o positivo mais específico (mais longo) vence — hoje o negativo sempre vence
  (`repository.py:1039`).

### 1.2 Ordenação por data em string corta oportunidades recentes 🔴

**Problema:** `repository.py:1024` — `ORDER BY data_disponibilizacao DESC` ordena string
`'dd/mm/yyyy'` lexicograficamente (`31/01/2026 > 01/12/2026`). Com `LIMIT` (50 API / 500
worker), oportunidades genuinamente recentes podem ser cortadas antes dos filtros em Python.

**Solução:** ordenar no SQL por `criado_em DESC` (timestamp real, correlaciona com coleta) —
mudança de 1 linha. Alternativa futura: coluna `data_disponibilizacao_date DATE` populada
por migração + trigger de normalização no insert.

### 1.3 Alerta criado antes da classificação existir (race) 🔴

**Problema:** `tasks.py:253-267` — o loop de alertas consulta `classificacoes_atuais` do DB
no mesmo tick em que as tasks de classificação foram **enfileiradas**. Processo novo → sem
classificação → alerta OPORTUNIDADE_CREDITO criado e notificado (telegram/email) mesmo que a
IA depois classifique DEVEDOR. A UI esconde, mas a notificação já saiu.

**Solução (encadeamento em 2 fases):**
- `varrer_oportunidades_task` enfileira classificações e **adia** os alertas dos processos
  sem classificação válida: envia `criar_alertas_oportunidade_task.send_with_options(
  args=..., delay=90_000)` (delay > tempo médio de classificação) OU
- melhor: `classificar_processo_task` ao terminar chama diretamente a criação de alerta para
  as pubs pendentes daquele processo (passa `pub_ids` candidatos como argumento).
- Processos **já classificados** continuam alertando de imediato (sem regressão de latência).
- Dedup permanece por `alerta_oportunidade_existe(pub_id)`.

### 1.4 Rerank descarta publicação ainda não indexada no Qdrant 🟡

**Problema:** `embedding_service.py:569-580` — `HasIdCondition` sobre os `pub_ids`: pub
coletada mas ainda não indexada (fila `indexacao` atrasada) não retorna ponto → tratada
como score baixo → descartada. O fail-safe só cobre exceção do Qdrant, não ausência do ponto.

**Solução:** após o `query_points`, fazer `client.retrieve(ids=ausentes)` para distinguir
"indexada com score < threshold" (descartar) de "não indexada" (manter com
`score_semantico = null`, deixando a classificação LLM decidir).

---

## FASE 2 — Valor e priorização (maior valor percebido)

### 2.1 Normalizar VALOR para numérico e ordenar por valor

A LLM já extrai `VALOR` mas fica string livre ("R$ 15.000,00" / "não identificado").

- Parser pt-BR (`R$ 1.234.567,89` → `Decimal`) em `classificacao_service` pós-parse;
  salvar em coluna nova `valor_numerico NUMERIC` em `classificacoes_processo` (migração 018).
- API `/oportunidades`: incluir `ia_valor_numerico`; UI: ordenação "Maior valor" no seletor
  existente de ordenação.
- Para o advogado, priorizar o alvará de R$ 500k sobre o de R$ 800 é o feature nº 1.

### 2.2 Structured outputs na classificação

Trocar parsing por regex (`_parsear_resposta`) por `response_format={"type": "json_schema"}`
do gpt-4o-mini. Elimina classe inteira de erros de parsing, custo igual, e o schema já
carrega `valor_numerico` direto. Bump do cache `_CLASSIF_CACHE_VERSION` v2→v3.

---

## FASE 3 — Recall e custo

### 3.1 Matching resiliente a acentos + índice

- Extensões Postgres `unaccent` + `pg_trgm`; índice GIN trigram em
  `publicacoes_monitoradas.texto_completo` (migração).
- Query passa a usar `unaccent(texto_completo) ILIKE unaccent(...)` — pega "alvara" de OCR.
- Resolve também a performance: hoje `%...%` com OR de N padrões é full scan.

### 3.2 Positivos também no texto_resumo

Inconsistência: o SQL só casa positivos em `texto_completo` (`repository.py:1011-1014`), mas
filtros negativo/intra-pub usam `texto_completo + texto_resumo`. Incluir `texto_resumo` no OR.

### 3.3 Invalidação de classificação mais inteligente

Hoje qualquer pub nova (mudança de `total_pubs`) re-chama a LLM — processos ativos com
despachos triviais semanais pagam reclassificação constante.

- Só reclassificar se a pub nova contém padrão positivo/negativo ou altera `polos_json`;
  senão, apenas atualizar `total_pubs` da classificação existente.

### 3.4 Threshold configurável

`0.45` hardcoded em `api.py:709` e `tasks.py:205` → `config.rerank_threshold`
(env `DJE_RERANK_THRESHOLD`, default 0.45), com possibilidade futura de override por tenant
via `tenants.settings`. Calibrar com os logs `_log_score_stats` já existentes no stage.

---

## FASE 4 — Arquitetura (materialização)

### 4.1 Tabela `oportunidades` materializada

Hoje o pipeline roda **duas vezes** com lógica duplicada: `GET /oportunidades` recomputa
tudo (ILIKE 90d + rerank Qdrant + batch) a cada request, e o worker repete na varredura.

- Nova tabela `oportunidades` (tenant_id, pub_id, pessoa_id, numero_processo, padrao,
  score_semantico, status, criado_em) preenchida/atualizada pela varredura.
- API só lê/filtra/pagina — GET instantâneo, paginação real, histórico e auditoria
  ("por que este processo saiu da lista?").
- Migração incremental: manter endpoint atual como fallback até validar no stage.

### 4.2 Feedback loop com descartes do usuário

`OportunidadeDescartada` é o dado de rotulagem mais valioso do sistema e hoje não alimenta nada.

- Métrica: % de itens descartados pelo usuário por aba (precisão percebida) — endpoint
  admin ou log periódico.
- Futuro: usar descartes como few-shot no prompt de classificação do tenant.

---

## Ordem de execução e riscos

| # | Item | Esforço | Risco | Deploy |
|---|------|---------|-------|--------|
| 1.1 | Padrões negativos/positivo "extinção pelo pagamento" | Baixo | Baixo (dados) | Script + API |
| 1.2 | Ordenação SQL por criado_em | 1 linha | Baixo | api+worker |
| 1.3 | Alertar só após classificar | Médio | Médio (fluxo de filas) | worker |
| 1.4 | Rerank não descarta não-indexadas | Baixo | Baixo | api+worker |
| 2.1 | Valor numérico + ordenação | Médio | Baixo | migração 018 + web |
| 2.2 | Structured outputs (cache v3) | Baixo | Baixo (reclassificação em massa 1x) | worker |
| 3.x | unaccent/trgm, resumo no OR, invalidação, threshold | Médio | Baixo | migração + api+worker |
| 4.x | Materialização + feedback loop | Alto | Médio | migração + tudo |

**Validação por fase:** deploy no stage → reprocessar tenant `demo`
(`DELETE FROM classificacoes_processo WHERE tenant_id=...` + `varrer_oportunidades_task.send(tid)`)
→ conferir abas na UI → só então tocar tenants reais (armando/viana-peixoto).

**Atenção:** 1.1 muda resultados para clientes reais — revisar com o usuário a lista final
de padrões negativos antes de aplicar nos tenants armando/viana-peixoto.
