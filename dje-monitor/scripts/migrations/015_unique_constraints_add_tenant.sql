-- Migration 015: Incluir tenant_id em todas as constraints/indexes unique
-- Sem isso, registros de tenants diferentes conflitam entre si

-- Constraints
ALTER TABLE classificacoes_processo DROP CONSTRAINT IF EXISTS uq_classif_pessoa_processo;
ALTER TABLE classificacoes_processo ADD CONSTRAINT uq_classif_tenant_pessoa_processo UNIQUE (tenant_id, pessoa_id, numero_processo);

ALTER TABLE diarios_processados DROP CONSTRAINT IF EXISTS uq_diario_tribunal_data_caderno_fonte;
ALTER TABLE diarios_processados ADD CONSTRAINT uq_diario_tenant_tribunal_data_caderno_fonte UNIQUE (tenant_id, tribunal, data_publicacao, caderno, fonte);

ALTER TABLE oportunidades_descartadas DROP CONSTRAINT IF EXISTS uq_descartada_pessoa_processo;
ALTER TABLE oportunidades_descartadas ADD CONSTRAINT uq_descartada_tenant_pessoa_processo UNIQUE (tenant_id, pessoa_id, numero_processo);

-- Indexes
DROP INDEX IF EXISTS ix_cpfs_monitorados_cpf;
CREATE UNIQUE INDEX ix_cpfs_monitorados_tenant_cpf ON cpfs_monitorados (tenant_id, cpf);

DROP INDEX IF EXISTS ix_publicacoes_monitoradas_hash_unico;
CREATE UNIQUE INDEX ix_publicacoes_monitoradas_tenant_hash ON publicacoes_monitoradas (tenant_id, hash_unico);
