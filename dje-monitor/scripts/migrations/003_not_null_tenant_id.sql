-- Migration 003: Tornar tenant_id NOT NULL após migração de dados
-- Executar SOMENTE após migrate_to_tenant_armando.py ter sido executado com sucesso
-- e todos os tenant_id estiverem preenchidos.

ALTER TABLE cpfs_monitorados ALTER COLUMN tenant_id SET NOT NULL;
ALTER TABLE diarios_processados ALTER COLUMN tenant_id SET NOT NULL;
ALTER TABLE ocorrencias ALTER COLUMN tenant_id SET NOT NULL;
ALTER TABLE pessoas_monitoradas ALTER COLUMN tenant_id SET NOT NULL;
ALTER TABLE publicacoes_monitoradas ALTER COLUMN tenant_id SET NOT NULL;
ALTER TABLE padroes_oportunidade ALTER COLUMN tenant_id SET NOT NULL;
ALTER TABLE classificacoes_processo ALTER COLUMN tenant_id SET NOT NULL;
ALTER TABLE oportunidades_descartadas ALTER COLUMN tenant_id SET NOT NULL;
ALTER TABLE alertas ALTER COLUMN tenant_id SET NOT NULL;
