-- Migration 021: assinatura de relevância na classificação (invalidação inteligente)
--
-- Antes, qualquer publicação nova (mudança de total_pubs) forçava reclassificação via LLM.
-- A sig_relevancia muda só quando o conteúdo relevante muda (pub com padrão positivo/
-- negativo ou alteração de polos), então despachos triviais não pagam nova chamada à LLM.
--
--   docker exec -i dje-monitor-postgres psql -U dje -d dje_monitor < 021_sig_relevancia.sql

ALTER TABLE classificacoes_processo
    ADD COLUMN IF NOT EXISTS sig_relevancia VARCHAR(40) NULL;
