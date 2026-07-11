# RadarJud — Apresentação Comercial

## Monitoramento Inteligente de Publicações Judiciais

---

## O que é o RadarJud?

O RadarJud é uma plataforma de monitoramento automatizado do Diário de Justiça Eletrônico (DJe). Ele acompanha, em tempo real, todas as movimentações processuais relevantes para o seu escritório — e ainda identifica oportunidades de crédito que muitas vezes passam despercebidas no volume diário de publicações.

Em vez de uma equipe dedicada à leitura manual de diários oficiais, o RadarJud faz esse trabalho de forma contínua, precisa e incansável.

---

## Para quem é o RadarJud?

- **Escritórios de advocacia** de qualquer porte
- **Departamentos jurídicos** de empresas
- **Advogados autônomos** que precisam acompanhar processos de múltiplos clientes
- **Consultorias de recuperação de créditos** judiciais

---

## Problema que resolvemos

Todo dia, milhares de publicações são veiculadas nos Diários de Justiça de todo o Brasil. Para um escritório que acompanha dezenas ou centenas de partes, a leitura manual é:

- **Demorada** — exige horas diárias de trabalho repetitivo
- **Sujeita a falhas** — publicações importantes podem ser perdidas por desatenção
- **Custosa** — requer pessoal dedicado exclusivamente a essa tarefa
- **Reativa** — quando a publicação é encontrada, o prazo já pode estar correndo

O RadarJud elimina esses problemas com automação inteligente e inteligência artificial.

---

## Funcionalidades Principais

### 1. Monitoramento Automático de Partes

Cadastre as pessoas ou empresas que deseja acompanhar — por nome, CPF ou CNPJ — e o sistema passa a verificar automaticamente as publicações do DJe em intervalos configuráveis (a cada 6, 12, 24 ou 48 horas).

**Destaques:**
- Cobertura de **27 tribunais estaduais**, tribunais federais e trabalhistas
- Possibilidade de filtrar por tribunal específico
- Importação em lote via **planilha Excel** — ideal para escritórios com grandes carteiras
- Prazo de expiração automática do monitoramento (configurável)
- Deduplicação inteligente: cada publicação é registrada uma única vez, sem repetições

### 2. Sistema de Alertas em Tempo Real

Toda vez que uma nova publicação é encontrada para uma parte monitorada, o sistema gera um alerta automaticamente.

**Destaques:**
- Painel com contador de alertas não lidos
- Filtros por pessoa, tipo de alerta e status de leitura
- Marcação individual ou em lote como "lido"
- Notificações opcionais por **Telegram** e **e-mail**

### 3. Detecção Automática de Oportunidades de Crédito

O grande diferencial do RadarJud: o sistema identifica automaticamente publicações que indicam possibilidade de recebimento de valores — como alvarás de levantamento, precatórios, RPVs, ordens de pagamento e desbloqueios.

**Como funciona:**
- O sistema utiliza **padrões configuráveis** (expressões de busca) para detectar termos relevantes nas publicações
- Padrões positivos identificam oportunidades; padrões negativos filtram falsos positivos
- Varredura automática a cada ciclo de verificação
- Janela de detecção de 90 dias para oportunidades, com alertas gerados nos primeiros 7 dias

**Exemplos de termos monitorados:**
- "Alvará de levantamento"
- "Mandado de levantamento"
- "Precatório"
- "RPV — Requisição de Pequeno Valor"
- "Ordem de pagamento"
- "Desbloqueio de valores"

### 4. Classificação por Inteligência Artificial

Cada oportunidade identificada pode ser analisada por inteligência artificial, que classifica automaticamente:

- **Papel da parte**: se é credor, devedor ou indefinido
- **Veredicto**: se há crédito identificado, crédito possível ou sem crédito
- **Valor estimado**: quando mencionado na publicação
- **Justificativa**: explicação em linguagem simples do motivo da classificação

Essa análise elimina a necessidade de leitura manual de cada publicação para entender seu impacto financeiro.

### 5. Resumo Inteligente de Processos

Com um clique, o sistema gera um resumo completo do histórico de um processo, consolidando todas as publicações encontradas em uma síntese clara e objetiva — escrita por IA, em linguagem acessível.

**O resumo inclui:**
- Contexto geral do processo
- Papel da parte monitorada (credor ou devedor)
- Avaliação sobre possibilidade de crédito
- Valor estimado, quando disponível

### 6. Busca Avançada

Além do monitoramento contínuo, o RadarJud oferece ferramentas de busca sob demanda:

- **Busca exata**: consulta direta ao DJe por nome da parte ou número de processo
- **Busca semântica (por inteligência artificial)**: encontra publicações relevantes mesmo quando os termos exatos não coincidem — útil para variações de nome, abreviações ou erros de grafia nos diários
- Resultados agrupados por processo, com histórico completo de publicações
- Indicadores visuais de relevância (verde, amarelo, vermelho)

### 7. Painel de Controle (Dashboard)

Visão consolidada do escritório em uma única tela:

- Total de publicações encontradas
- Pessoas monitoradas ativas
- Alertas não lidos
- Oportunidades de crédito identificadas
- Horário da última sincronização
- Últimas movimentações em tempo real

### 8. Parametrização Flexível

O escritório tem total controle sobre os critérios de detecção de oportunidades:

- Criação e edição de padrões de busca (positivos e negativos)
- Ativação/desativação individual de cada padrão
- Ordenação por prioridade (arraste e solte)
- Ajuste fino para reduzir falsos positivos e aumentar a precisão

---

## Diferenciais Competitivos

### Inteligência Artificial Aplicada
Não se trata apenas de busca por palavras-chave. O RadarJud utiliza modelos de IA de última geração para:
- Compreender o **contexto** das publicações, não apenas os termos isolados
- Classificar automaticamente o papel da parte e a existência de crédito
- Gerar resumos que economizam horas de leitura manual

### Isolamento Total por Cliente (Multi-tenancy)
Cada escritório opera em um ambiente completamente isolado:
- Dados de um cliente nunca se misturam com os de outro
- Buscas, alertas, oportunidades e configurações são exclusivos de cada conta
- Segurança de nível bancário na separação dos dados

### Segurança Robusta
- Autenticação com tokens JWT (padrão utilizado por bancos e fintechs)
- Senhas criptografadas com algoritmo bcrypt
- Controle de tentativas de login (bloqueio automático após 5 tentativas)
- Registro completo de auditoria (quem acessou, quando, de onde)
- Proteção contra acesso não autorizado em todas as camadas

### Perfis de Acesso Diferenciados
O sistema suporta 5 níveis de permissão:

| Perfil | Acesso |
|--------|--------|
| **Proprietário** | Acesso total, gestão de usuários e configurações |
| **Administrador** | Gestão da equipe e configurações do escritório |
| **Advogado** | Buscas, monitoramento, visualização de oportunidades |
| **Estagiário** | Leitura da maioria dos dados, ações limitadas |
| **Somente leitura** | Visualização sem possibilidade de alteração |

### Processamento Paralelo e Escalável
- Verificações são distribuídas entre múltiplos processadores simultâneos
- O sistema cresce junto com o escritório — sem perda de desempenho
- Arquitetura preparada para milhares de partes monitoradas simultaneamente

---

## Como funciona no dia a dia?

### Para o gestor do escritório:
1. **Manhã**: Abre o Dashboard e vê quantos alertas surgiram durante a noite
2. Revisa as **oportunidades de crédito** identificadas pela IA
3. Distribui as tarefas relevantes para os advogados da equipe

### Para o advogado:
1. Acessa o sistema, lê o **resumo inteligente** gerado pela IA
2. Toma a providência necessária dentro do prazo

### Para o escritório como um todo:
- **Nenhuma publicação importante é perdida**
- **Oportunidades de crédito são identificadas automaticamente**
- **Horas de trabalho manual são economizadas diariamente**
- **Prazos são cumpridos com mais segurança**

---

## Automações em Funcionamento

O RadarJud trabalha 24 horas por dia, 7 dias por semana, executando automaticamente:

| Rotina | Frequência | Função |
|--------|-----------|--------|
| Verificação de partes | A cada 30 minutos | Busca novas publicações para todas as partes ativas |
| Varredura de oportunidades | A cada ciclo | Identifica publicações com potencial de crédito |
| Indexação de publicações | Contínua | Mantém a base de busca semântica atualizada |
| Reindexação completa | Diária (02h) | Garante consistência total da base de dados |
| Limpeza de segurança | Diária (03h) | Remove tokens expirados e registros antigos |
| Desativação automática | Contínua | Encerra monitoramentos que atingiram o prazo de expiração |

---

## Cobertura de Tribunais

O RadarJud consulta o Diário de Justiça Eletrônico de todos os tribunais disponíveis na base do DJe Nacional:

- **27 Tribunais de Justiça Estaduais** (TJSP, TJRJ, TJMG, etc.)
- **Tribunais Regionais Federais** (TRF1 a TRF6)
- **Tribunais Regionais do Trabalho**
- Filtro por tribunal disponível em todas as funcionalidades

---

## Importação Facilitada

Já possui uma carteira de partes monitoradas? Importe tudo de uma vez:

1. Prepare uma **planilha Excel** com os nomes das partes adversárias
2. Faça upload pelo sistema
3. O RadarJud oferece um modo de **simulação** (dry-run) para validação antes da importação definitiva
4. Todas as partes são cadastradas e começam a ser monitoradas imediatamente

---

## Infraestrutura e Confiabilidade

- **Banco de dados PostgreSQL 16** — o mesmo utilizado por grandes empresas de tecnologia
- **Armazenamento vetorial Qdrant** — tecnologia de ponta para busca semântica
- **Cache Redis** — respostas rápidas mesmo com grande volume de dados
- **Arquitetura em containers Docker** — deploy simplificado e escalável
- **Backup e recuperação** — dados protegidos contra perda

---

## Fluxo de Onboarding

A implantação do RadarJud é rápida e simples:

1. **Criação do ambiente** do escritório (isolado e seguro)
2. **Cadastro do usuário administrador**
3. **Importação da carteira** de partes (via planilha ou cadastro manual)
4. **Configuração dos padrões** de detecção de oportunidades (já vem com padrões pré-configurados)
5. **Pronto para usar** — o monitoramento automático começa imediatamente

---

## Proposta de Valor

| Sem RadarJud | Com RadarJud |
|-------------|-------------|
| Leitura manual de diários oficiais | Monitoramento 100% automatizado |
| Publicações perdidas por volume | Nenhuma publicação relevante escapa |
| Horas de trabalho repetitivo | Equipe focada em atividades estratégicas |
| Oportunidades de crédito não identificadas | IA detecta e classifica oportunidades automaticamente |
| Controle por planilhas | Dashboard centralizado e em tempo real |
| Risco de perda de prazos | Alertas instantâneos por múltiplos canais |
| Sem histórico organizado | Base de dados pesquisável com busca inteligente |

---

## Resumo Executivo

O **RadarJud** é uma solução completa de monitoramento judicial que combina automação, inteligência artificial e segurança de dados para transformar a forma como escritórios de advocacia acompanham publicações do Diário de Justiça Eletrônico.

**Principais entregas:**
- Monitoramento automático e contínuo de partes em todos os tribunais
- Detecção inteligente de oportunidades de crédito
- Classificação e resumo por inteligência artificial
- Alertas em tempo real (plataforma, Telegram, e-mail)
- Busca avançada com tecnologia semântica
- Segurança e isolamento total dos dados por cliente
- Importação em massa e configuração flexível

**Resultado:** mais eficiência, menos risco, mais receita.

---

*RadarJud — Seu radar no Diário de Justiça.*
