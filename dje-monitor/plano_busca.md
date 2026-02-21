Essa funcionalidade merece uma abordagem própria na interface. Deixa eu propor um design antes de implementar.

Proposta: Nova aba "Oportunidades" na página de Busca
A ideia é uma busca especializada que varre automaticamente todas as pessoas monitoradas procurando publicações com sinais de patrimônio:


┌─────────────────────────────────────────────────────────────┐
│  Busca Exata    Busca Semântica    Oportunidades de Crédito  │
├─────────────────────────────────────────────────────────────┤
│  Devedores com sinais de recebimento de valores             │
│                                                             │
│  Período: [Últimos 30 dias ▾]   [Buscar]                   │
├─────────────────────────────────────────────────────────────┤
│  JANE MARY ABUHASSAN GONÇALVES              TJMS  02/02/26  │
│  0809813-05.2023.8.12.0001                                  │
│  "Expeça-se alvará de levantamento em favor da parte..."    │
│  [Ver publicação]  [Abrir processo]                         │
├─────────────────────────────────────────────────────────────┤
│  LUCIO MACHADO DA SILVA                     TJRS  15/01/26  │
│  5017492-44.2022.8.21.0015                                  │
│  "Mandado de levantamento para soerguimento do depósito..." │
│  [Ver publicação]  [Abrir processo]                         │
└─────────────────────────────────────────────────────────────┘
O que o backend precisaria
Um novo endpoint que faz a varredura diretamente no texto_completo de todos os monitorados:


GET /api/v1/oportunidades?dias=30&limit=50
Critérios de detecção:

alvará + (levantamento ou pagamento)
mandado de levantamento
expedição de precatório
exequente aparecendo junto com o nome da pessoa (ela como credora)
Perguntas antes de implementar
Algumas decisões que impactam o design:

Onde colocar? Nova aba na página Busca, ou página separada no menu?
Atualização? Rodando automaticamente a cada sync ou só quando o usuário clicar em "Buscar"?
Notificação? Quando aparecer uma oportunidade nova, gerar um alerta especial diferente dos alertas normais?
Quer que eu já implemente, ou tem preferências sobre algum desses pontos?

respostas:

Onde colocar? página separada no menu
Atualização? as duas Rodando automaticamente a cada sync e quando o usuário clicar em "Buscar"
Notificação? Quando aparecer uma oportunidade nova, gerar um alerta especial diferente dos alertas normais- sim