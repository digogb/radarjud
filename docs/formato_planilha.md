● A planilha deve ser um arquivo .xlsx com a primeira linha como cabeçalho. As colunas reconhecidas são:

  ┌────────────────────┬─────────────┬───────────────────────────────────────────────┐
  │       Coluna       │ Obrigatória │                    Exemplo                    │
  ├────────────────────┼─────────────┼───────────────────────────────────────────────┤
  │ Parte Adversa      │     Sim     │ AUTOR - LUCIO MACHADO DA SILVA ou MARIA SILVA │
  ├────────────────────┼─────────────┼───────────────────────────────────────────────┤
  │ CPF/CNPJ Adverso   │     Não     │ 123.456.789-00 ou 12345678000199              │
  ├────────────────────┼─────────────┼───────────────────────────────────────────────┤
  │ Número do Processo │     Não     │ 0001234-56.2023.8.06.0001 ou só dígitos       │
  ├────────────────────┼─────────────┼───────────────────────────────────────────────┤
  │ Data Prazo         │     Não     │ 15/03/2024 ou 15/03/2024 14:30:00             │
  ├────────────────────┼─────────────┼───────────────────────────────────────────────┤
  │ Comarca            │     Não     │ Fortaleza                                     │
  ├────────────────────┼─────────────┼───────────────────────────────────────────────┤
  │ UF                 │     Não     │ CE                                            │
  └────────────────────┴─────────────┴───────────────────────────────────────────────┘


  ┌───────────────┬───────────────────────────────────────────────────────────────────────────────┐
  │     Campo     │                               Variações aceitas                               │
  ├───────────────┼───────────────────────────────────────────────────────────────────────────────┤
  │ Parte Adversa │ Parte Adversa, Nome, Nome Adverso, Parte Contrária, Adversário, Nome da Parte │
  ├───────────────┼───────────────────────────────────────────────────────────────────────────────┤
  │ CPF/CNPJ      │ CPF/CNPJ Adverso, CPF/CNPJ, CPF, CNPJ, Documento, Doc                         │
  ├───────────────┼───────────────────────────────────────────────────────────────────────────────┤
  │ Processo      │ Número do Processo, Processo, Nº Processo, Num Processo                       │
  ├───────────────┼───────────────────────────────────────────────────────────────────────────────┤
  │ Data Prazo    │ Data Prazo, Data do Prazo, Prazo, Dt Prazo, Vencimento                        │
  ├───────────────┼───────────────────────────────────────────────────────────────────────────────┤
  │ Comarca       │ Comarca, Foro, Vara                                                           │
  ├───────────────┼───────────────────────────────────────────────────────────────────────────────┤
  │ UF            │ UF, Estado, Sigla UF, Sigla Estado                                            │
  └───────────────┴───────────────────────────────────────────────────────────────────────────────┘

  Detalhes:
  - Só "Parte Adversa" é obrigatória — as demais são opcionais
  - O nome é extraído após o - (ex: AUTOR - JOÃO SILVA → JOÃO SILVA)
  - CPF (11 dígitos) e CNPJ (14 dígitos) são aceitos, com ou sem formatação
  - Data de expiração é calculada automaticamente como data_prazo + 5 anos
  - A ordem das colunas não importa — o sistema busca pelo nome do cabeçalho