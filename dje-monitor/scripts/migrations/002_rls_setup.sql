-- Migration 002: Configurar Row-Level Security (RLS)
-- Executar DEPOIS de 001_add_tenant_id.sql e 003_migrate_to_armando.sql
-- (RLS só deve ser ativado após todos os dados terem tenant_id preenchido)

-- Criar role da aplicação (se não existir)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user WITH LOGIN PASSWORD 'app_user_password';
    END IF;
END $$;

GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app_user;

-- Habilitar RLS nas tabelas com tenant_id
ALTER TABLE cpfs_monitorados ENABLE ROW LEVEL SECURITY;
ALTER TABLE diarios_processados ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocorrencias ENABLE ROW LEVEL SECURITY;
ALTER TABLE pessoas_monitoradas ENABLE ROW LEVEL SECURITY;
ALTER TABLE publicacoes_monitoradas ENABLE ROW LEVEL SECURITY;
ALTER TABLE padroes_oportunidade ENABLE ROW LEVEL SECURITY;
ALTER TABLE classificacoes_processo ENABLE ROW LEVEL SECURITY;
ALTER TABLE oportunidades_descartadas ENABLE ROW LEVEL SECURITY;
ALTER TABLE alertas ENABLE ROW LEVEL SECURITY;

-- A tabela tenants é pública (leitura) — não tem RLS, pois o middleware valida o tenant
-- Mas escrita é restrita ao superuser/admin

-- Políticas RLS: cada tabela só retorna rows do tenant setado na sessão
-- O valor vem de: SET LOCAL app.current_tenant = '<uuid>'

CREATE POLICY tenant_isolation ON cpfs_monitorados
    USING (tenant_id = current_setting('app.current_tenant', true)::VARCHAR);

CREATE POLICY tenant_isolation ON diarios_processados
    USING (tenant_id = current_setting('app.current_tenant', true)::VARCHAR);

CREATE POLICY tenant_isolation ON ocorrencias
    USING (tenant_id = current_setting('app.current_tenant', true)::VARCHAR);

CREATE POLICY tenant_isolation ON pessoas_monitoradas
    USING (tenant_id = current_setting('app.current_tenant', true)::VARCHAR);

CREATE POLICY tenant_isolation ON publicacoes_monitoradas
    USING (tenant_id = current_setting('app.current_tenant', true)::VARCHAR);

CREATE POLICY tenant_isolation ON padroes_oportunidade
    USING (tenant_id = current_setting('app.current_tenant', true)::VARCHAR);

CREATE POLICY tenant_isolation ON classificacoes_processo
    USING (tenant_id = current_setting('app.current_tenant', true)::VARCHAR);

CREATE POLICY tenant_isolation ON oportunidades_descartadas
    USING (tenant_id = current_setting('app.current_tenant', true)::VARCHAR);

CREATE POLICY tenant_isolation ON alertas
    USING (tenant_id = current_setting('app.current_tenant', true)::VARCHAR);

-- NOTA: superusers e roles com BYPASSRLS bypassam essas políticas automaticamente.
-- Para que a aplicação respeite o RLS, ela deve conectar como 'app_user'
-- (não como superuser). Configurar DJE_DATABASE_URL com app_user.
-- Para migrations, continuar usando o superuser.
