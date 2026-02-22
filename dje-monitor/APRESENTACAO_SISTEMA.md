# DJE Monitor — Documento de Produto
### Base para Apresentação e Proposta Comercial

---

## 1. O Problema

Advogados, escritórios de cobrança e credores que monitoram devedores no sistema judiciário brasileiro enfrentam um gargalo operacional crítico: **o volume de publicações no Diário da Justiça Eletrônico (DJE) é imenso e cresce diariamente**.

Acompanhar manualmente centenas de processos em múltiplos tribunais significa:

- Verificar portais de tribunais todos os dias, manualmente
- Risco de perder publicações críticas por desatenção ou sobrecarga
- Custo de horas de trabalho repetitivo que não gera valor jurídico
- Atraso na identificação de oportunidades de recebimento de crédito
- Impossibilidade de monitorar em escala (centenas ou milhares de réus simultaneamente)

**A consequência prática**: oportunidades de recebimento de crédito são perdidas, prazos são descumpridos e a produtividade das equipes jurídicas é desperdiçada em tarefas operacionais.

---

## 2. A Solução — DJE Monitor

O **DJE Monitor** é uma plataforma de monitoramento automático e inteligente de publicações judiciais. O sistema acompanha pessoas e empresas no DJE de todos os tribunais brasileiros, detecta publicações relevantes em tempo real e identifica automaticamente sinais de oportunidade de recebimento de crédito.

### Em uma frase
> Monitoramento automatizado, contínuo e inteligente do Diário da Justiça — com alertas em tempo real e detecção de oportunidades de crédito.

---

## 3. Para Quem

O DJE Monitor é voltado a:

| Perfil | Caso de Uso |
|--------|-------------|
| **Escritórios de advocacia** | Monitorar réus, devedores e partes adversas em múltiplos processos |
| **Empresas de cobrança** | Detectar sinais de pagamento (alvarás, precatórios, levantamentos) |
| **Credores com carteira de processos** | Acompanhar o andamento de execuções judiciais em escala |
| **Gestores de precatórios** | Rastrear publicações relacionadas a expedição e pagamento de precatórios |
| **Fintechs jurídicas** | Integrar monitoramento como serviço via API |

---

## 4. Funcionalidades Principais

### 4.1 Monitoramento Automatizado de Partes

O usuário cadastra o nome (ou CPF/CNPJ) de uma pessoa ou empresa. O sistema passa a monitorar automaticamente todas as publicações do DJE nacional que envolvam essa parte, em todos os tribunais configurados.

- Frequência configurável: a cada 6h, 12h, 24h ou 48h
- Suporte a todos os tribunais estaduais, federais e trabalhistas
- Deduplicação automática — a mesma publicação nunca é notificada duas vezes
- Monitoramento com data de expiração (controle de prazo)
- Importação em massa via planilha Excel

### 4.2 Alertas Inteligentes

Toda nova publicação encontrada gera um alerta. Os alertas são:

- Exibidos em tempo real na interface
- Categorizados por tipo: **Nova Publicação** ou **Oportunidade de Crédito**
- Enviados por **Telegram** e/ou **e-mail** (configurável)
- Controláveis: marcar como lido individualmente ou em massa

### 4.3 Detecção de Oportunidades de Crédito

O módulo de oportunidades identifica automaticamente publicações que sinalizam **possibilidade de recebimento de valores**:

**Padrões positivos (configura pelo usuário):**
- Expedição de precatório
- Alvará de levantamento / pagamento
- Mandado de levantamento
- RPV (Requisição de Pequeno Valor)
- Acordo homologado
- Ordem de pagamento

**Filtro negativo (evita falsos positivos):**
O sistema verifica se, para o mesmo processo, existe uma publicação **mais recente** contendo termos que invalidam a oportunidade (anulação, cassação, suspensão, revogação, extinção). Se encontrar, o processo é automaticamente excluído da lista de oportunidades.

Todos os padrões — positivos e negativos — são **configuráveis pelo próprio usuário** pela interface, sem necessidade de intervenção técnica.

### 4.4 Busca Semântica com Inteligência Artificial

Além da busca por palavras exatas, o sistema oferece **busca semântica por contexto jurídico**:

- O usuário descreve o que procura em linguagem natural
- O sistema encontra publicações semanticamente relacionadas, mesmo sem correspondência exata de palavras
- Resultados ranqueados por grau de relevância (score de similaridade)
- Funciona tanto para publicações individuais quanto para histórico completo de processos

**Exemplo**: buscar por _"execução fiscal com penhora de imóvel"_ encontra processos que abordam esse tema, mesmo que o texto use termos diferentes.

### 4.5 Busca Direta no DJE

Para consultas pontuais (sem necessidade de monitoramento), o usuário pode:

- Pesquisar publicações por nome de parte ou número CNJ de processo
- Filtrar por tribunal
- Ver o histórico completo do processo em uma visão lateral (drawer)
- Adicionar a parte diretamente ao monitoramento a partir dos resultados

---

## 5. Diferenciais Competitivos

| Diferencial | Descrição |
|-------------|-----------|
| **Cobertura nacional** | Todos os tribunais via DJEN (API oficial do CNJ) |
| **Detecção de oportunidades de crédito** | Identificação automática de alvarás, precatórios e levantamentos |
| **Filtro negativo inteligente** | Evita falsos positivos verificando anulações posteriores |
| **Busca semântica em português** | Modelo de linguagem treinado em português jurídico (BERT-BR) |
| **Configuração sem código** | Padrões de detecção gerenciáveis pelo próprio usuário |
| **Importação em massa** | Carga de carteiras inteiras via planilha Excel |
| **Notificações multicanal** | Telegram + e-mail integrados |
| **Arquitetura robusta** | Processamento assíncrono, sem perda de dados em caso de falha |

---

## 6. Interface do Usuário

O sistema possui uma interface web moderna, acessível por qualquer navegador, organizada em 5 seções:

### Dashboard
Visão geral: total de publicações encontradas, alertas não lidos, última sincronização e resumo de atividade recente.

### Busca
Pesquisa direta no DJE por nome ou número de processo. Permite alternar entre busca exata e busca semântica (IA). Exibe resultados agrupados por processo com histórico completo.

### Monitorados
Lista de todas as pessoas/empresas em monitoramento. Para cada monitorado: total de publicações, alertas pendentes, data do último e próximo check, data de expiração. Permite adicionar, editar, remover e importar em lote.

### Oportunidades
Lista de processos com sinais de oportunidade de crédito. Filtros por período (7, 30, 60, 90 dias), nome e número de processo. Badges coloridos por tipo de oportunidade detectada. Ordenação por data, nome ou quantidade de publicações.

### Parametrização
Configuração dos padrões de detecção, separados em duas abas:
- **Padrões Positivos**: palavras que indicam oportunidade de crédito
- **Padrões Negativos**: palavras que invalidam uma oportunidade (anulação, etc.)

Cada padrão pode ser ativado/desativado individualmente ou em massa. A ordem de prioridade é ajustável por arrastar e soltar.

---

## 7. Arquitetura Técnica

### 7.1 Visão Geral

```
┌─────────────────────────────────────────────┐
│           Interface Web (React)              │
│   Dashboard · Busca · Monitorados            │
│   Oportunidades · Parametrização             │
└──────────────────┬──────────────────────────┘
                   │ REST API
       ┌───────────▼──────────────┐
       │     Backend (FastAPI)    │
       │  - API REST              │
       │  - Agendador (30 min)    │
       │  - Workers assíncronos   │
       └───┬──────────┬───────────┘
           │          │
  ┌────────▼──┐  ┌────▼──────────────────────┐
  │PostgreSQL │  │   Processamento Paralelo   │
  │(dados)    │  │   (Dramatiq + Redis)       │
  └────────┬──┘  └────┬──────────────────────┘
           │          │
           └────┬─────┘
                │
         ┌──────▼──────┐
         │   Qdrant    │
         │ (vetores /  │
         │busca semân.)│
         └─────────────┘
```

### 7.2 Componentes

| Componente | Tecnologia | Papel |
|------------|-----------|-------|
| **Frontend** | React 18 + TypeScript + Vite | Interface do usuário (SPA) |
| **Backend** | Python + FastAPI | API REST, agendamento, lógica de negócio |
| **Banco de Dados** | PostgreSQL 16 | Armazenamento relacional de dados |
| **Fila de Tarefas** | Dramatiq + Redis | Processamento assíncrono e paralelo |
| **Busca Vetorial** | Qdrant | Banco de vetores para busca semântica |
| **Modelo de IA** | nomic-embed-text-v1.5 (256 dims) | Geração de embeddings para busca semântica |
| **Coleta de Dados** | DJEN API (CNJ) | Fonte oficial de publicações judiciais |
| **Deploy** | Docker Compose | Containerização e orquestração |
| **Web Server** | Nginx | Servir o frontend em produção |

### 7.3 Fluxo de Monitoramento Automatizado

```
A cada 30 minutos:
  1. Agendador seleciona pessoas com verificação pendente
  2. Para cada pessoa: consulta DJEN (API oficial do CNJ)
  3. Novas publicações são salvas (deduplicação por hash único)
  4. Alertas gerados para publicações novas
  5. Publicações indexadas no Qdrant (embeddings)
  6. Notificações enviadas (Telegram / e-mail)
  7. Varredura de oportunidades de crédito:
     a. Publica com padrões positivos → candidato a oportunidade
     b. Verifica padrões negativos em publicações mais recentes
     c. Somente aprovados geram alerta de oportunidade
```

### 7.4 Escalabilidade

- Processamento paralelo com workers independentes
- Filas resilientes: tarefas sobrevivem a reinicializações
- Batch processing: até 500 monitoramentos por ciclo
- Rate limiting configurável para não sobrecarregar a API do CNJ
- Volumes persistentes para dados e vetores

---

## 8. Integração com Fontes de Dados

### DJEN — Diário da Justiça Eletrônico Nacional

A plataforma integra com a **API oficial do Conselho Nacional de Justiça (CNJ)** para coleta de publicações:

- **Cobertura**: Todos os 27 tribunais estaduais (TJSP, TJCE, TJRJ, etc.), tribunais federais e trabalhistas
- **Dados coletados**: número do processo (CNJ), data de disponibilização, órgão julgador, tipo de comunicação, polos ativo e passivo, texto integral da publicação
- **Frequência**: Configurável por monitorado (6h a 48h)
- **Autenticação**: Via API key (quando aplicável)

---

## 9. Segurança e Privacidade

- Dados armazenados localmente na infraestrutura do cliente (on-premises ou cloud privada)
- Nenhum dado é compartilhado com terceiros além da API pública do CNJ
- Acesso à interface protegido por autenticação (a ser configurada conforme ambiente)
- Comunicação entre serviços via rede Docker interna (não exposta)
- Variáveis sensíveis (senhas, tokens) isoladas em arquivo `.env`

---

## 10. Modelo de Implantação

### Opção A — On-Premises (Servidor do Cliente)
O sistema é implantado no servidor ou VM do próprio cliente. Requer:
- Servidor Linux (Ubuntu 22.04 recomendado)
- Docker + Docker Compose instalados
- 4 vCPU, 8 GB RAM, 50 GB disco (mínimo)
- Acesso à internet (para consultar o DJEN)

### Opção B — Cloud (Servidor Dedicado)
O sistema é implantado em servidor cloud (AWS, GCP, Azure, Oracle Cloud, etc.), gerenciado pela equipe técnica. Inclui:
- Configuração, deploy e manutenção do ambiente
- Monitoramento de uptime
- Backups automatizados

### Opção C — SaaS Multi-tenant _(roadmap)_
Versão compartilhada em nuvem, com isolamento de dados por cliente. Modelo de assinatura por volume de monitorados.

---

## 11. Requisitos de Infraestrutura

### Mínimo (desenvolvimento / piloto)
| Recurso | Mínimo |
|---------|--------|
| CPU | 2 vCPU |
| RAM | 4 GB |
| Disco | 20 GB |
| SO | Ubuntu 22.04 LTS |

### Recomendado (produção)
| Recurso | Recomendado |
|---------|-------------|
| CPU | 4–8 vCPU |
| RAM | 8–16 GB |
| Disco | 100 GB SSD |
| Rede | 100 Mbps+ |

> O uso de GPU é **opcional** — o modelo de embeddings opera em CPU sem degradação significativa para volumes moderados (até 10.000 publicações/dia).

---

## 12. Roadmap Sugerido

| Fase | Funcionalidade | Status |
|------|---------------|--------|
| ✅ v1.0 | Monitoramento básico + alertas | Entregue |
| ✅ v1.1 | Busca semântica com IA | Entregue |
| ✅ v1.2 | Detecção de oportunidades de crédito | Entregue |
| ✅ v1.3 | Padrões negativos configuráveis + abas | Entregue |
| ✅ v1.4 | Importação Excel + notificações | Entregue |
| 🔄 v2.0 | Autenticação multi-usuário com perfis | Planejado |
| 🔄 v2.1 | Dashboard analítico com gráficos | Planejado |
| 🔄 v2.2 | API pública para integração de terceiros | Planejado |
| 🔄 v2.3 | Modelo SaaS multi-tenant | Planejado |
| 🔄 v3.0 | Resumo automático de publicações com LLM | Planejado |
| 🔄 v3.1 | Classificação automática de tipo de oportunidade | Planejado |

---

## 13. Métricas de Valor

Com base na capacidade atual da plataforma, um escritório de médio porte pode esperar:

| Métrica | Cenário |
|---------|---------|
| **Monitorados simultâneos** | Sem limite técnico (escalável horizontalmente) |
| **Frequência de verificação** | A cada 6 horas (até 4x ao dia por monitorado) |
| **Tempo de detecção** | < 6h após publicação no DJE |
| **Falsos positivos** | Reduzidos pelo filtro negativo + reranking semântico |
| **Horas salvas por analista/mês** | Estimativa: 40–80h para carteiras de 200+ processos |

---

## 14. Glossário Técnico

| Termo | Definição |
|-------|-----------|
| **DJE / DJEN** | Diário da Justiça Eletrônico (Nacional) — publicação oficial das decisões judiciais |
| **CNJ** | Conselho Nacional de Justiça — órgão que disponibiliza a API de publicações |
| **Embedding** | Representação numérica (vetor) de um texto, usada para busca semântica |
| **Qdrant** | Banco de dados especializado em vetores (busca por similaridade) |
| **Dramatiq** | Framework Python para processamento assíncrono de tarefas (workers) |
| **FastAPI** | Framework web Python de alta performance para APIs REST |
| **Padrão Positivo** | Expressão textual que indica oportunidade de crédito em uma publicação |
| **Padrão Negativo** | Expressão que, em publicação mais recente, invalida uma oportunidade |
| **Hash Único** | Identificador gerado a partir do conteúdo da publicação — garante deduplicação |
| **Reranking Semântico** | Reclassificação de resultados por similaridade vetorial, reduzindo falsos positivos |

---

*Documento gerado em fevereiro de 2026.*
*Para mais informações técnicas, consultar `plano_parametrizacao.md`.*
