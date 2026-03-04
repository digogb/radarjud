-- Migration 011: Criação da tabela de refresh tokens

CREATE TABLE refresh_tokens (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL,           -- SHA-256 do token (nunca armazenar plain)
    family_id VARCHAR(36) NOT NULL,             -- Para token rotation detection
    is_revoked BOOLEAN DEFAULT false,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    replaced_by VARCHAR(36) REFERENCES refresh_tokens(id)  -- Rastreabilidade
);

CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens(token_hash) WHERE NOT is_revoked;
CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_family ON refresh_tokens(family_id);
CREATE INDEX idx_refresh_tokens_expired ON refresh_tokens(expires_at) WHERE NOT is_revoked;
