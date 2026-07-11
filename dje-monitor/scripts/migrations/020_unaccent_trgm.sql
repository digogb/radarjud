-- Migration 020: matching de oportunidades resiliente a acentos + índice de performance
--
-- Habilita unaccent (remove acentos) e pg_trgm (índice para ILIKE '%...%'), e cria
-- um índice GIN trigram sobre texto_completo — hoje o matching de N padrões com OR de
-- ILIKE é full scan. Com pg_trgm o planner pode usar o índice.
--
-- Rodar como superuser `dje` (CREATE EXTENSION exige superuser):
--   docker exec -i dje-monitor-postgres psql -U dje -d dje_monitor < 020_unaccent_trgm.sql

CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- unaccent é STABLE por padrão, mas o planner só usa índice em expressão com função
-- IMMUTABLE. Índice trigram direto sobre a coluna acelera o ILIKE; a normalização de
-- acento é resolvida em tempo de query (o volume por tenant é baixo).
CREATE INDEX IF NOT EXISTS idx_pub_texto_completo_trgm
    ON publicacoes_monitoradas USING gin (texto_completo gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_pub_texto_resumo_trgm
    ON publicacoes_monitoradas USING gin (texto_resumo gin_trgm_ops);
