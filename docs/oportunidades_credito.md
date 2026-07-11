# Funcionalidade de Oportunidades de Crédito

## O que faz

O sistema monitora publicações do **Diário de Justiça Eletrônico (DJe)** para encontrar sinais de que uma pessoa monitorada tem dinheiro a receber em um processo judicial. É útil para escritórios de advocacia ou assessorias que acompanham devedores e precisam saber quando esses devedores, em **outros processos**, são credores.

## Exemplo concreto

Imagine que você monitora **EVERALDO DE OLIVEIRA BORGES** porque ele te deve dinheiro. O sistema varre as publicações do DJe e encontra:

> *"Fica(m) a(s) Parte(s), intimada(s) do evento processual ocorrido... depositar em Juízo o valor da condenação apurado no evento 40..."*

A publicação contém o padrão **"Art. 523"** — que é um sinal de crédito. Mas quem é credor aqui? O EVERALDO está sendo **intimado a pagar**, então ele é o **devedor** neste processo. Antes da classificação IA, o sistema marcava ele como "Credor" incorretamente.

## Como funciona (3 camadas)

```
┌─────────────────────────────────────────────────────┐
│  CAMADA 1: Detecção por palavras-chave              │
│  "alvará de levantamento", "precatório", "RPV"...   │
│  Custo: R$ 0,00 (local)                             │
│  Roda: a cada 30min (cron) ou ao clicar "Analisar"  │
├─────────────────────────────────────────────────────┤
│  CAMADA 2: Filtro semântico (Qdrant)                │
│  Embedding local — descarta falsos positivos        │
│  Custo: R$ 0,00 (modelo local nomic-embed)          │
│  Roda: junto com a camada 1                         │
├─────────────────────────────────────────────────────┤
│  CAMADA 3: Classificação IA (OpenAI gpt-4o-mini)   │
│  Determina se a pessoa é CREDOR ou DEVEDOR          │
│  Custo: ~$0.0001 por processo (~R$ 0,0006)          │
│  Roda: proativamente após camada 2                  │
├─────────────────────────────────────────────────────┤
│  BÔNUS: Resumo completo (sob demanda)               │
│  Gera timeline + papel + valor + status             │
│  Custo: ~$0.003 por processo (~R$ 0,018)            │
│  Roda: quando o usuário clica "Resumir processo"    │
└─────────────────────────────────────────────────────┘
```

## Cache inteligente

A classificação é salva em **2 camadas de cache**:

- **Redis**: TTL de 7 dias, acesso instantâneo
- **PostgreSQL**: persistente, usado como fallback

A chave do cache inclui o `total_pubs` (quantidade de publicações). Se uma nova publicação aparece para o mesmo processo, o cache é **automaticamente invalidado** e a classificação roda novamente.

## Previsão de custos (OpenAI)

Dados reais da instalação (48 processos classificados):

| Métrica | Classificação (batch) | Resumo (sob demanda) |
|---------|----------------------|---------------------|
| **Modelo** | gpt-4o-mini | gpt-4o-mini |
| **Input médio** | 676 tokens | ~2.000 tokens |
| **Output médio** | 54 tokens | ~800 tokens |
| **Custo/chamada** | **$0.00012** | **$0.003** |
| **Quando roda** | Automático (proativo) | Quando clica "Resumir" |

> Preços gpt-4o-mini (março 2026): input $0.15/1M tokens, output $0.60/1M tokens.

### Cenários de uso mensal

| Cenário | Pessoas monit. | Processos/mês | Classificações | Resumos (10%) | Custo mensal |
|---------|---------------|---------------|----------------|---------------|-------------|
| **Pequeno** | 10 | ~30 | 30 | 3 | **$0.013** (~R$ 0,08) |
| **Médio** | 50 | ~200 | 200 | 20 | **$0.084** (~R$ 0,50) |
| **Grande** | 200 | ~1.000 | 1.000 | 100 | **$0.42** (~R$ 2,50) |

O cache faz com que classificações não se repitam — se o processo não mudou, usa o resultado salvo. Na prática, após a primeira rodada (que classificou 48 processos por $0.006), as próximas varreduras só classificam processos **novos** ou com **novas publicações**.

## Abas na interface

- **Oportunidades** (aba padrão): Processos onde a pessoa é CREDOR com `CREDITO_IDENTIFICADO`, `CREDITO_POSSIVEL`, ou ainda sem classificação
- **Descartados pela IA**: Processos onde a IA identificou que a pessoa é `DEVEDOR` ou `SEM_CREDITO`
