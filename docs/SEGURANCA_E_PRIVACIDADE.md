# RadarJud — Seguranca e Privacidade de Dados

**Documento Tecnico de Seguranca da Informacao**
Versao 1.0 — Abril 2026

---

## 1. Visao Geral

Este documento descreve as medidas tecnicas e organizacionais de seguranca da informacao implementadas na plataforma RadarJud, abrangendo:

- Arquitetura e isolamento de dados
- Autenticacao e controle de acesso
- Protecao de dados em transito e em repouso
- Infraestrutura e hospedagem
- Auditoria e rastreabilidade
- Conformidade com LGPD

O RadarJud foi projetado para operar em ambiente multi-tenant, garantindo que os dados de cada organizacao (escritorio, empresa ou departamento) sejam completamente isolados dos demais.

---

## 2. Arquitetura de Seguranca

### 2.1 Isolamento de Dados por Tenant (Multi-Tenancy)

Cada organizacao opera em um **tenant** isolado. O isolamento e implementado em multiplas camadas:

| Camada | Mecanismo | Descricao |
|--------|-----------|-----------|
| **Banco de dados** | Row-Level Security (RLS) | Politicas de seguranca a nivel de linha no PostgreSQL. Cada consulta e automaticamente filtrada pelo `tenant_id` do usuario autenticado. Mesmo em caso de falha no codigo da aplicacao, o banco impede acesso cruzado entre tenants. |
| **Sessao de banco** | `SET app.current_tenant` | Cada conexao ao banco define o tenant via variavel de sessao, ativando as politicas RLS antes de qualquer consulta. |
| **Usuario de banco** | `app_user` (sem superuser) | A aplicacao conecta com um usuario sem privilegios administrativos — o RLS e obrigatoriamente aplicado pelo PostgreSQL. |
| **Busca vetorial** | Collections separadas no Qdrant | Dados de busca semantica sao armazenados em collections fisicamente separadas por tenant (`dje_{tenant_id}_publicacoes` e `dje_{tenant_id}_processos`). |
| **Cache** | Prefixo por tenant no Redis | Chaves de cache seguem o padrao `t:{tenant_id}:{chave}`, impedindo colisao entre tenants. |

### 2.2 Diagrama de Isolamento

```
Cliente A (Escritorio X)              Cliente B (Escritorio Y)
        |                                      |
   [JWT com tenant_id=A]               [JWT com tenant_id=B]
        |                                      |
        v                                      v
  +------------------+               +------------------+
  |   API Gateway    |               |   API Gateway    |
  | (valida JWT,     |               | (valida JWT,     |
  |  extrai tenant)  |               |  extrai tenant)  |
  +--------+---------+               +--------+---------+
           |                                   |
           v                                   v
  +--------------------------------------------------+
  |              PostgreSQL com RLS                   |
  |  SET app.current_tenant = 'A'                     |
  |  -> So ve dados do tenant A                       |
  |                                                   |
  |  SET app.current_tenant = 'B'                     |
  |  -> So ve dados do tenant B                       |
  +--------------------------------------------------+
```

---

## 3. Autenticacao e Controle de Acesso

### 3.1 Autenticacao

| Aspecto | Implementacao |
|---------|---------------|
| **Protocolo** | JWT (JSON Web Tokens) com algoritmo HS256 |
| **Access Token** | Validade de 30 minutos, armazenado exclusivamente em memoria do navegador (nao persistido) |
| **Refresh Token** | Validade de 30 dias, armazenado em `sessionStorage` (encerrado ao fechar a aba). Rotacao obrigatoria: cada token so pode ser usado uma unica vez |
| **Deteccao de reuso** | Se um refresh token ja utilizado for apresentado novamente, toda a familia de sessoes e revogada automaticamente (indicativo de ataque) |
| **Hash de senhas** | bcrypt com 12 rounds de salt |
| **Senha temporaria** | Ao criar usuario, uma senha aleatoria e gerada e exibida uma unica vez. O usuario e obrigado a trocar no primeiro acesso (`must_change_password`) |

### 3.2 Protecao contra Forca Bruta

| Mecanismo | Configuracao |
|-----------|-------------|
| **Lockout por conta** | Apos 5 tentativas falhas, a conta e bloqueada por 15 minutos |
| **Rate limiting por IP** | Maximo de 20 tentativas de login por IP a cada 15 minutos |
| **Fail-secure** | Se o servico de rate limiting estiver indisponivel, o login e bloqueado (nao degradado) |

### 3.3 Controle de Acesso Baseado em Papeis (RBAC)

O sistema implementa 5 niveis de acesso com permissoes granulares:

| Permissao | Owner | Admin | Advogado | Estagiario | Leitura |
|-----------|:-----:|:-----:|:--------:|:----------:|:-------:|
| Visualizar processos e publicacoes | Sim | Sim | Sim | Sim | Sim |
| Busca semantica | Sim | Sim | Sim | Sim | Sim |
| Cadastrar pessoa monitorada | Sim | Sim | Sim | Sim | Nao |
| Editar monitoramento | Sim | Sim | Sim | Nao | Nao |
| Excluir monitoramento | Sim | Sim | Nao | Nao | Nao |
| Gerenciar usuarios | Sim | Sim | Nao | Nao | Nao |
| Alterar papeis | Sim | Sim* | Nao | Nao | Nao |
| Configuracoes do tenant | Sim | Nao | Nao | Nao | Nao |
| Audit log | Sim | Sim | Nao | Nao | Nao |
| Exportar dados | Sim | Sim | Sim | Nao | Nao |

\* Admin pode alterar papeis de advogado, estagiario e leitura, mas nao de outros admins ou owners.

Toda requisicao a API e validada por autenticacao JWT e verificacao de permissao antes de processar a operacao.

---

## 4. Protecao de Dados

### 4.1 Dados em Transito

| Componente | Protecao |
|------------|----------|
| **Cliente <-> Servidor** | TLS 1.2+ via HTTPS com certificado Let's Encrypt (renovacao automatica) |
| **HSTS** | `Strict-Transport-Security: max-age=31536000; includeSubDomains` — navegadores sao instruidos a sempre usar HTTPS |
| **Servicos internos** | Comunicacao via rede Docker isolada (bridge network), sem exposicao de portas a internet |

### 4.2 Dados em Repouso

| Componente | Protecao |
|------------|----------|
| **Disco da VM** | OCI Block Volume com criptografia AES-256 gerenciada pela Oracle (encryption at rest padrao) |
| **PostgreSQL** | Dados armazenados em volume Docker persistente sobre disco criptografado da OCI |
| **Credenciais de servico** | Armazenadas em variaveis de ambiente, nunca no codigo-fonte |

### 4.3 Dados Processados

O RadarJud processa exclusivamente dados publicos do Diario da Justica Eletronica. Os dados armazenados incluem:

- Nomes de partes monitoradas
- CPFs (quando fornecidos para refinamento de busca)
- Textos de publicacoes judiciais (informacao publica)
- Numeros de processos

**O sistema nao armazena**: dados bancarios, documentos pessoais, contratos ou informacoes financeiras dos usuarios.

---

## 5. Headers de Seguranca HTTP

Todas as respostas da API incluem os seguintes headers de protecao:

| Header | Valor | Finalidade |
|--------|-------|------------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Forca HTTPS |
| `X-Content-Type-Options` | `nosniff` | Impede MIME sniffing |
| `X-Frame-Options` | `DENY` | Impede embedding em iframes (clickjacking) |
| `X-XSS-Protection` | `1; mode=block` | Protecao contra XSS refletido |
| `Content-Security-Policy` | `default-src 'self'; script-src 'self'; ...` | Restringe fontes de conteudo permitidas |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limita vazamento de URL em referrers |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` | Desabilita APIs de hardware desnecessarias |
| `Cache-Control` | `no-store` | Impede cache de respostas sensiveis |

---

## 6. Infraestrutura e Hospedagem

### 6.1 Oracle Cloud Infrastructure (OCI)

| Aspecto | Detalhe |
|---------|---------|
| **Provedor** | Oracle Cloud Infrastructure |
| **Regiao** | sa-saopaulo-1 (Sao Paulo, Brasil) |
| **Tipo de instancia** | VM.Standard.A1.Flex (Ampere ARM) |
| **Residencia dos dados** | Brasil — dados nunca saem do territorio nacional |

### 6.2 Certificacoes do Datacenter (herdadas da OCI)

A infraestrutura Oracle Cloud onde o RadarJud esta hospedado possui as seguintes certificacoes:

- **ISO/IEC 27001:2013** — Gestao de Seguranca da Informacao
- **ISO/IEC 27017:2015** — Seguranca para servicos em nuvem
- **ISO/IEC 27018:2019** — Protecao de dados pessoais em nuvem
- **SOC 1 Type II** — Controles de relatorio financeiro
- **SOC 2 Type II** — Seguranca, disponibilidade e confidencialidade
- **SOC 3** — Relatorio publico de controles
- **PCI DSS** — Padrao de seguranca de dados de cartoes
- **CSA STAR** — Cloud Security Alliance

Referencia: https://www.oracle.com/br/corporate/cloud-compliance/

### 6.3 Arquitetura de Rede

```
Internet
    |
    v
[OCI Security List / Firewall]
    |  Portas permitidas: 80 (redirect), 443 (HTTPS)
    v
[Nginx - Reverse Proxy + TLS Termination]
    |
    v (rede Docker interna — sem acesso externo)
    +---> [API FastAPI :8000]
    +---> [Worker Dramatiq]
    +---> [PostgreSQL :5432] (autenticado)
    +---> [Redis :6379] (autenticado)
    +---> [Qdrant :6333] (autenticado com API key)
```

Nenhum servico interno (banco de dados, cache, busca vetorial) esta exposto a internet. O acesso e exclusivamente via rede Docker interna, com autenticacao obrigatoria em cada servico.

---

## 7. Auditoria e Rastreabilidade

### 7.1 Audit Log

O sistema registra automaticamente os seguintes eventos em tabela dedicada (`auth_audit_log`):

| Evento | Dados registrados |
|--------|-------------------|
| Login bem-sucedido | usuario, IP, user-agent, timestamp |
| Falha de login | usuario (se encontrado), IP, user-agent |
| Conta bloqueada | usuario, IP |
| Logout | usuario |
| Criacao de usuario | quem criou, email e role do novo usuario |
| Alteracao de role | quem alterou, role anterior e novo |
| Desativacao de conta | quem desativou, usuario alvo |
| Reset de senha | quem resetou, usuario alvo |

Os logs sao retidos no banco de dados e acessiveis via API apenas por usuarios com papel **owner** ou **admin**.

### 7.2 Limpeza Automatica

Tokens de refresh expirados e logs de auditoria antigos sao removidos automaticamente por jobs agendados (diariamente as 03:00), garantindo que dados desnecessarios nao sejam retidos indefinidamente.

---

## 8. Conformidade com LGPD

### 8.1 Base Legal

O tratamento de dados pelo RadarJud se enquadra nas seguintes bases legais da LGPD (Lei 13.709/2018):

| Dado | Base Legal | Fundamento |
|------|-----------|------------|
| Nomes de partes processuais | Art. 7o, X — Protecao do credito | Monitoramento de publicacoes para protecao de direitos crediticios |
| CPFs fornecidos pelo usuario | Art. 7o, I — Consentimento | Usuario fornece voluntariamente para refinamento de busca |
| Publicacoes do DJE | Art. 7o, X e Art. 7o, III | Dados publicos por forca de lei (principio da publicidade processual) |
| Dados de usuarios do sistema | Art. 7o, V — Execucao de contrato | Necessarios para prestacao do servico contratado |

### 8.2 Principios Atendidos

| Principio LGPD | Como e atendido |
|-----------------|-----------------|
| **Finalidade** | Dados sao coletados exclusivamente para monitoramento de publicacoes judiciais |
| **Adequacao** | Apenas dados necessarios ao monitoramento sao armazenados |
| **Necessidade** | Minimizacao: CPF e opcional, textos de publicacao sao dados ja publicos |
| **Seguranca** | Criptografia em transito e repouso, isolamento por tenant, controle de acesso granular |
| **Prevencao** | Rate limiting, lockout, deteccao de reuso de token, fail-secure |
| **Nao discriminacao** | Dados nao sao utilizados para profiling ou decisoes automatizadas sobre titulares |

### 8.3 Direitos do Titular

O sistema suporta o exercicio dos direitos dos titulares (Art. 18 da LGPD):

- **Acesso**: o administrador do tenant pode exportar dados de pessoas monitoradas
- **Eliminacao**: pessoas monitoradas podem ser desativadas e seus dados removidos
- **Revogacao**: CPFs podem ser removidos do monitoramento a qualquer momento

---

## 9. Gestao de Vulnerabilidades

### 9.1 Dependencias

- Dependencias Python gerenciadas via `requirements.txt` com versoes fixas
- Imagens Docker baseadas em versoes estáveis (`python:3.11-slim`, `postgres:16-alpine`, `redis:7-alpine`)
- Atualizacoes de seguranca aplicadas periodicamente

### 9.2 Protecoes Implementadas

| Vulnerabilidade (OWASP) | Mitigacao |
|--------------------------|-----------|
| **Injection (SQL)** | ORM SQLAlchemy com queries parametrizadas + RLS no PostgreSQL |
| **Broken Authentication** | JWT com rotacao, lockout, rate limiting, bcrypt |
| **Sensitive Data Exposure** | Mensagens de erro sanitizadas, sem stack traces ao cliente |
| **Broken Access Control** | RBAC com 5 niveis, verificacao em cada endpoint |
| **Security Misconfiguration** | Headers de seguranca, CSP, servicos internos autenticados |
| **XSS** | Content-Security-Policy, X-XSS-Protection, sanitizacao de entrada |
| **CSRF** | API stateless (JWT Bearer), sem cookies de sessao |

---

## 10. Disponibilidade

| Aspecto | Implementacao |
|---------|---------------|
| **Restart automatico** | Todos os containers configurados com `restart: unless-stopped` |
| **Health checks** | PostgreSQL e Redis com verificacoes periodicas de saude |
| **Pool de conexoes** | PostgreSQL com pool de 10 conexoes + 20 overflow, com `pool_pre_ping` |
| **Workers independentes** | Processamento de monitoramento em workers separados — falha no worker nao afeta a API |

---

## 11. Contato

Para questoes relacionadas a seguranca da informacao ou exercicio de direitos LGPD:

- **Responsavel tecnico**: [a definir pelo contratante]
- **Email**: [a definir]

---

*Documento gerado em abril de 2026. Versao 1.0.*
*Ultima revisao de seguranca do codigo: 16/04/2026.*
