-- Migration 012: Criação da tabela de audit log de autenticação

CREATE TABLE auth_audit_log (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id),
    user_id VARCHAR(36) REFERENCES users(id),
    action VARCHAR(50) NOT NULL,   -- 'login', 'login_failed', 'login_blocked', 'logout',
                                   -- 'password_reset', 'user_created', 'user_deactivated', 'role_changed'
    ip_address VARCHAR(45),        -- IPv4 ou IPv6
    user_agent TEXT,
    details JSONB DEFAULT '{}',    -- Dados adicionais (ex: role anterior/novo)
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_audit_tenant_date ON auth_audit_log(tenant_id, created_at DESC);
CREATE INDEX idx_audit_user ON auth_audit_log(user_id, created_at DESC);
