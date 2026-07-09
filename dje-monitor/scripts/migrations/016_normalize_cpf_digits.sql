-- Migration 016: Normalizar CPF/CNPJ existentes para apenas dígitos
-- Motivo: coluna cpf é varchar(14); valores formatados (ex.: CNPJ '12.345.678/0001-90' = 18 chars)
-- estouravam o limite e causavam erro 500 no cadastro. A partir de agora o app grava só dígitos;
-- esta migration alinha os dados já existentes e a deduplicação por cpf.

UPDATE pessoas_monitoradas
SET cpf = regexp_replace(cpf, '[^0-9]', '', 'g')
WHERE cpf IS NOT NULL
  AND cpf ~ '[^0-9]';

UPDATE cpfs_monitorados
SET cpf = regexp_replace(cpf, '[^0-9]', '', 'g')
WHERE cpf IS NOT NULL
  AND cpf ~ '[^0-9]';
