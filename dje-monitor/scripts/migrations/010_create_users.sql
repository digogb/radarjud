-- Migration 010: Criação da tabela de usuários
-- Rodar APÓS as migrations 001, 002, 003 (multi-tenancy)

CREATE TYPE user_role AS ENUM ('owner', 'admin', 'advogado', 'estagiario', 'leitura');

CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'leitura',
    is_active BOOLEAN DEFAULT true,

    -- Controle de acesso
    last_login_at TIMESTAMPTZ,
    password_changed_at TIMESTAMPTZ DEFAULT now(),
    failed_login_attempts INT DEFAULT 0,
    locked_until TIMESTAMPTZ,
    must_change_password BOOLEAN DEFAULT false,

    -- Metadata
    created_by VARCHAR(36) REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    -- Email único por tenant
    CONSTRAINT uq_user_email_tenant UNIQUE (tenant_id, email)
);

CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_tenant_active ON users(tenant_id, is_active) WHERE is_active = true;

-- RLS: usuários só veem outros usuários do mesmo tenant
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_users ON users
    USING (tenant_id = current_setting('app.current_tenant', true)::VARCHAR);
