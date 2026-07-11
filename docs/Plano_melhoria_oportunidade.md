Plano: Classificação Automática de Credor/Devedor via LLM
Contexto e Problema
O que está errado hoje
A funcionalidade de Oportunidades opera em 3 camadas:

ILIKE — encontra publicações com palavras-chave como "alvará de levantamento", "precatório"
Reranking semântico (Qdrant) — confirma relevância semântica do texto (score > 0.45)
Filtro de polo (polos_json) — tenta excluir devedores comparando nome contra polo ativo/passivo
O problema: a camada 3 falha frequentemente porque polos_json vem incompleto da API DJEN. Resultado: processos onde a pessoa monitorada é devedora (intimada a pagar) aparecem na lista como "Credor" ou "Polo indefinido". A LLM, ao ser chamada sob demanda, corretamente identifica como DEVEDOR — mas o dano já foi feito (falso positivo na lista).

Além disso, o prompt atual no resumo_service.py tem um viés: na linha 151 diz "ela é devedora em outro processo" — assumindo que toda pessoa monitorada é devedora buscando créditos. Isso pode confundir o modelo.

O que queremos
Máxima assertividade: para cada processo detectado por keyword, saber com certeza se a pessoa monitorada é credora (vai receber) ou devedora (deve pagar). Fazer isso proativamente na varredura, com custo otimizado de tokens.

Decisões do usuário
Prompt neutro: não assumir que a pessoa é devedora. Deixar o modelo decidir baseado exclusivamente nas publicações. Corrigir também o prompt do resumo_service.py (linha 151) que tem viés.
3 estados na aba principal: CREDITO_IDENTIFICADO + CREDITO_POSSIVEL + sem classificação ficam na aba "Oportunidades". Só SEM_CREDITO + DEVEDOR vão para "Descartados pela IA".
Geração proativa na varredura: classificação roda automaticamente ao detectar oportunidades.
Descartados em aba separada: não esconde, permite revisão manual.
Decisão Arquitetural: Dois Prompts, Dois Momentos
Por que não um prompt só?
Classificação (batch)	Resumo completo (sob demanda)
Quando	Na varredura (varrer_oportunidades_task)	Clique em "Resumir processo"
Input	2-3 publicações mais recentes, 500 chars cada	Todas publicações, 1500 chars cada
Output	~50-80 tokens (PAPEL + VEREDICTO + VALOR + 1 frase)	~800-1400 tokens (resumo Markdown completo)
Custo estimado	~$0.0003/processo	~$0.002/processo
Volume	15-50 processos por ciclo	Apenas os que o usuário clica
Para 50 processos por ciclo:

Classificação batch: ~$0.015 (~R$0.08)
Resumo completo batch: ~$0.10 (~R$0.55)
A classificação é 7x mais barata porque usa menos input (publicações truncadas) e muito menos output. Para o batch proativo, faz sentido economizar. O resumo completo fica para quando o usuário realmente quer ler.

Otimização de input para classificação
A chave para economia de tokens é: para classificar credor/devedor, não precisamos de toda a história do processo. As publicações mais recentes (2-3) já indicam o status atual. E 500 chars por publicação capturam o trecho relevante (intimação, decisão, etc).

Economia: ~2000-3000 tokens de input (classificação) vs ~5000-12000 (resumo) = 60-75% menos input.

Arquitetura Proposta
Fluxo Completo

varrer_oportunidades_task (existente)
  │
  ├── 1. buscar_oportunidades(dias=7) ← keyword + negativo + polo (como hoje)
  │      retorna ~50-200 candidatos
  │
  ├── 2. rerank_oportunidades() ← Qdrant semântico (como hoje)
  │      retorna ~15-50 aprovados
  │
  ├── 3. [NOVO] Agrupar por (pessoa_id, numero_processo) ← únicos
  │      ~10-30 processos distintos
  │
  ├── 4. [NOVO] Para cada processo: checar classificacao no Redis/DB
  │      ├── Se existe e pub_count não mudou → usar cache (skip LLM)
  │      └── Se não existe ou invalidado → enfileirar classificar_processo_task
  │
  ├── 5. [NOVO] classificar_processo_task (fila "classificacao")
  │      ├── Buscar 3 publicações mais recentes (500 chars cada)
  │      ├── Chamar OpenAI com prompt CURTO de classificação
  │      ├── Parsear PAPEL / VEREDICTO / VALOR
  │      ├── Salvar em tabela classificacoes_processo (DB)
  │      └── Salvar em Redis cache (7 dias)
  │
  └── 6. Criar alertas OPORTUNIDADE_CREDITO (como hoje)
         Mas agora SÓ para processos com papel != DEVEDOR
Fluxo do Endpoint GET /api/v1/oportunidades

GET /api/v1/oportunidades?dias=30&limit=50
  │
  ├── buscar_oportunidades() ← keyword + filtros (como hoje)
  ├── rerank_oportunidades() ← Qdrant (como hoje, se semantico=true)
  │
  ├── [NOVO] Enriquecer cada item com classificação do DB
  │   LEFT JOIN classificacoes_processo ON (pessoa_id, numero_processo_digits)
  │   → cada item ganha: ia_papel, ia_veredicto, ia_valor
  │
  └── Retornar tudo (frontend separa em abas)
Fluxo do Frontend

Página Oportunidades
  │
  ├── Tab "Oportunidades" (default)
  │   └── Processos com ia_veredicto IN (CREDITO_IDENTIFICADO, CREDITO_POSSIVEL, NULL)
  │       - NULL = ainda não classificado (mostra "Aguardando IA..." ou spinner)
  │       - Badge: usa ia_papel quando disponível, senão polo_pessoa (fallback)
  │
  ├── Tab "Descartados pela IA"
  │   └── Processos com ia_veredicto = SEM_CREDITO OU ia_papel = DEVEDOR
  │       - Badge vermelho "Devedor" + "Sem Crédito"
  │       - Permite revisão manual
  │
  └── Drawer (existente)
      ├── Badges: usa ia_papel/ia_veredicto/ia_valor (do DB, não da LLM on-demand)
      ├── Botão "Resumir processo" → gera resumo COMPLETO (prompt longo)
      └── ResumoCard: resumo narrativo + badges (como hoje)
Modelo de Dados
Nova tabela: classificacoes_processo

CREATE TABLE classificacoes_processo (
    id              SERIAL PRIMARY KEY,
    pessoa_id       INTEGER NOT NULL REFERENCES pessoas_monitoradas(id),
    numero_processo VARCHAR(30) NOT NULL,     -- normalizado (só dígitos)
    papel           VARCHAR(20),              -- CREDOR | DEVEDOR | INDEFINIDO
    veredicto       VARCHAR(30),              -- CREDITO_IDENTIFICADO | CREDITO_POSSIVEL | SEM_CREDITO
    valor           VARCHAR(100),             -- "R$ 50.000,00" ou "não identificado"
    justificativa   VARCHAR(500),             -- 1 frase explicando a classificação
    total_pubs      INTEGER NOT NULL,         -- para invalidação automática
    criado_em       TIMESTAMP DEFAULT NOW(),
    atualizado_em   TIMESTAMP DEFAULT NOW(),
    UNIQUE (pessoa_id, numero_processo)       -- uma classificação por processo/pessoa
);
Cache Redis
Classificação:

Chave: classif:v1:{pessoa_id}:{proc_digits}:{total_pubs}
Valor: JSON {papel, veredicto, valor, justificativa}
TTL: 7 dias
Invalidação automática por total_pubs
Resumo completo (existente):

Chave: resumo:v2:{pessoa_id}:{proc}:{total_pubs}
Sem mudanças
Prompt de Classificação (otimizado, NEUTRO)

SISTEMA (~180 tokens):
Você é um analista jurídico especializado em execuções judiciais brasileiras.

Dadas publicações recentes do DJe sobre um processo, determine:
1. O PAPEL da parte monitorada neste processo específico (credora ou devedora)
2. Se há crédito a receber pela parte monitorada

Sinais de CREDOR: alvará/mandado de levantamento EM FAVOR da parte, precatório a receber,
RPV, acordo em que a parte recebe, depósito judicial a ser levantado pela parte.

Sinais de DEVEDOR: intimação para pagar/depositar, penhora de bens da parte,
cumprimento de sentença contra a parte, condenação da parte a pagar.

Responda APENAS neste formato (sem explicação adicional):
PAPEL: [CREDOR | DEVEDOR | INDEFINIDO]
VEREDICTO: [CREDITO_IDENTIFICADO | CREDITO_POSSIVEL | SEM_CREDITO]
VALOR: [valor em reais ou "não identificado"]
JUSTIFICATIVA: [1 frase curta]

USUÁRIO (~800-2000 tokens):
Parte monitorada: EVERALDO DE OLIVEIRA BORGES
Processo: 0029225-76.2025.8.05.0001
Polo ativo: [nomes do polos_json, se disponível]
Polo passivo: [nomes do polos_json, se disponível]

Publicações mais recentes (até 3):
[27/06/2025] Despacho — 14ª VSJE DO CONSUMIDOR
Fica(m) a(s) Parte(s), por seu(s) Advogado(s), intimada(s) do evento processual
ocorrido... depositar em Juízo o valor da condenação apurada no evento 40...
Output esperado (~50-80 tokens):


PAPEL: DEVEDOR
VEREDICTO: SEM_CREDITO
VALOR: não identificado
JUSTIFICATIVA: A parte monitorada está sendo intimada a depositar o valor da condenação, indicando posição de executada/devedora neste processo.
Correção no resumo_service.py (prompt do resumo completo)
Linha 151 atual:


f"(ela é devedora em outro processo e estamos verificando se possui créditos a receber neste)"
Substituir por (neutro):


f"(estamos verificando seu papel neste processo — pode ser credora ou devedora)"
Implementação — Arquivos a Modificar
1. src/storage/models.py
Adicionar modelo ClassificacaoProcesso (SQLAlchemy)
2. src/storage/repository.py
salvar_classificacao(pessoa_id, numero_processo, papel, veredicto, valor, justificativa, total_pubs) — upsert
obter_classificacao(pessoa_id, numero_processo) → dict ou None
obter_classificacoes_batch(lista_de_tuples) → dict de classificações
buscar_oportunidades() — enriquecer resultado com LEFT JOIN em classificacoes_processo
3. src/services/classificacao_service.py (novo)
classificar_processo(publicacoes, api_key, modelo, pessoa_nome, numero_processo) → {papel, veredicto, valor, justificativa}
Prompt curto e focado
Input: últimas 3 publicações, 500 chars cada
Output: ~50-80 tokens
4. src/tasks.py
Novo actor classificar_processo_task (fila classificacao)
Busca publicações do processo
Checa cache Redis
Se miss: chama classificacao_service.classificar_processo()
Salva no DB + Redis
Modificar varrer_oportunidades_task:
Após detectar oportunidades, agrupar por processo
Para cada processo sem classificação válida: enfileirar classificar_processo_task
Só criar alertas para processos com papel != DEVEDOR (ou sem classificação ainda)
5. src/api.py
GET /api/v1/oportunidades — enriquecer items com ia_papel, ia_veredicto, ia_valor do DB
POST /api/v1/oportunidades/resumo — manter como está (resumo completo sob demanda)
Novo: POST /api/v1/oportunidades/classificar — dispara classificação manual de um processo
6. web/src/services/api.ts
Atualizar OportunidadeItem com campos ia_papel, ia_veredicto, ia_valor
7. web/src/pages/Oportunidades.tsx
Adicionar sistema de abas: "Oportunidades" e "Descartados pela IA"
Badge na lista usa ia_papel quando disponível, senão fallback para polo_pessoa
Tab "Descartados" mostra processos com ia_papel === 'DEVEDOR' ou ia_veredicto === 'SEM_CREDITO'
Indicador "Classificando..." para processos sem classificação ainda
8. src/config.py
DJE_CLASSIF_MAX_PUBS (default: 3) — quantas publicações enviar para classificação
DJE_CLASSIF_MAX_CHARS (default: 500) — chars por publicação na classificação
9. docker-compose.yml
Adicionar fila classificacao ao worker (se necessário)
Estratégia de Cache Detalhada

Processo detectado como oportunidade
  │
  ├── 1. Checar Redis: classif:v1:{pessoa_id}:{proc}:{pub_count}
  │      ├── HIT → usar classificação cacheada, pular LLM
  │      └── MISS → continuar
  │
  ├── 2. Checar DB: classificacoes_processo WHERE pessoa_id AND numero_processo
  │      ├── HIT + total_pubs == atual → copiar pro Redis, pular LLM
  │      ├── HIT + total_pubs != atual → invalidar, continuar (nova pub adicionada)
  │      └── MISS → continuar
  │
  ├── 3. Chamar OpenAI (classificação curta)
  │
  └── 4. Salvar em:
         ├── Redis (TTL 7 dias)
         └── DB (persistente, com upsert)
Invalidação automática: quando total_pubs muda (nova publicação no processo), a chave Redis é diferente e o DB é atualizado via upsert.

Verificação / Teste
Unitário: testar classificacao_service.classificar_processo() com mock do OpenAI
Integração: testar varrer_oportunidades_task com mock do OpenAI e verificar que:
Processos DEVEDOR não geram alerta
Classificação é persistida no DB
Manual end-to-end:
Rodar varredura
Verificar no Redis que classificações foram cacheadas
Abrir página Oportunidades → aba principal só mostra credores
Clicar na aba "Descartados" → mostra devedores
Clicar "Resumir processo" → resumo completo funciona como antes
Adicionar nova publicação a um processo → classificação roda novamente
Custo: monitorar tokens usados nos logs após deploy