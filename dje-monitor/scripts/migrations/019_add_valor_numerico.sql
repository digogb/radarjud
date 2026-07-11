-- Migration 019: valor numérico da classificação, para ordenar oportunidades por valor.
-- A LLM já extraía o valor como texto; agora persistimos também o número.
--
-- Rodar como superuser `dje` (bypassa RLS):
--   docker exec -i dje-monitor-postgres psql -U dje -d dje_monitor < 019_add_valor_numerico.sql

ALTER TABLE classificacoes_processo
    ADD COLUMN IF NOT EXISTS valor_numerico NUMERIC(15, 2) NULL;
