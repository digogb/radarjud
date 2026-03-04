-- Migration 001: Adicionar tenant_id em todas as tabelas
-- Executar como superuser ou app_admin
-- IMPORTANTE: Executar ANTES de 002_rls_setup.sql e 003_migrate_to_armando.sql

-- Tabela: cpfs_monitorados
ALTER TABLE cpfs_monitorados
    ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(36) REFERENCES tenants(id);
CREATE INDEX IF NOT EXISTS idx_cpfs_monitorados_tenant ON cpfs_monitorados(tenant_id);

-- Tabela: diarios_processados
ALTER TABLE diarios_processados
    ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(36) REFERENCES tenants(id);
CREATE INDEX IF NOT EXISTS idx_diarios_processados_tenant ON diarios_processados(tenant_id);

-- Tabela: ocorrencias
ALTER TABLE ocorrencias
    ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(36) REFERENCES tenants(id);
CREATE INDEX IF NOT EXISTS idx_ocorrencias_tenant ON ocorrencias(tenant_id);

-- Tabela: pessoas_monitoradas
ALTER TABLE pessoas_monitoradas
    ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(36) REFERENCES tenants(id);
CREATE INDEX IF NOT EXISTS idx_pessoas_monitoradas_tenant ON pessoas_monitoradas(tenant_id);
CREATE INDEX IF NOT EXISTS idx_pessoas_monitoradas_tenant_nome ON pessoas_monitoradas(tenant_id, nome);

-- Tabela: publicacoes_monitoradas
ALTER TABLE publicacoes_monitoradas
    ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(36) REFERENCES tenants(id);
CREATE INDEX IF NOT EXISTS idx_publicacoes_monitoradas_tenant ON publicacoes_monitoradas(tenant_id);

-- Tabela: padroes_oportunidade
ALTER TABLE padroes_oportunidade
    ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(36) REFERENCES tenants(id);
CREATE INDEX IF NOT EXISTS idx_padroes_oportunidade_tenant ON padroes_oportunidade(tenant_id);

-- Tabela: classificacoes_processo
ALTER TABLE classificacoes_processo
    ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(36) REFERENCES tenants(id);
CREATE INDEX IF NOT EXISTS idx_classificacoes_processo_tenant ON classificacoes_processo(tenant_id);

-- Tabela: oportunidades_descartadas
ALTER TABLE oportunidades_descartadas
    ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(36) REFERENCES tenants(id);
CREATE INDEX IF NOT EXISTS idx_oportunidades_descartadas_tenant ON oportunidades_descartadas(tenant_id);

-- Tabela: alertas
ALTER TABLE alertas
    ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(36) REFERENCES tenants(id);
CREATE INDEX IF NOT EXISTS idx_alertas_tenant ON alertas(tenant_id);
