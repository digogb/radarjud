-- Migration 014: Tornar tenant_id NOT NULL em todas as tabelas
-- Pré-requisito: todos os registros já devem ter tenant_id preenchido

ALTER TABLE alertas ALTER COLUMN tenant_id SET NOT NULL;
ALTER TABLE classificacoes_processo ALTER COLUMN tenant_id SET NOT NULL;
ALTER TABLE cpfs_monitorados ALTER COLUMN tenant_id SET NOT NULL;
ALTER TABLE diarios_processados ALTER COLUMN tenant_id SET NOT NULL;
ALTER TABLE ocorrencias ALTER COLUMN tenant_id SET NOT NULL;
ALTER TABLE oportunidades_descartadas ALTER COLUMN tenant_id SET NOT NULL;
ALTER TABLE padroes_oportunidade ALTER COLUMN tenant_id SET NOT NULL;
ALTER TABLE pessoas_monitoradas ALTER COLUMN tenant_id SET NOT NULL;
ALTER TABLE publicacoes_monitoradas ALTER COLUMN tenant_id SET NOT NULL;
