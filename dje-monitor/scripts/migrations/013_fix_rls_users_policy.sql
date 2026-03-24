-- Migration 013: Corrigir política RLS da tabela users
-- A tabela users precisa permitir acesso completo ao app_user
-- porque o auth service faz login/refresh sem tenant context definido.
-- A segurança de tenant na tabela users é garantida pelo auth service (JWT).

-- Remover policy restritiva original (se existir)
DROP POLICY IF EXISTS tenant_isolation_users ON users;
DROP POLICY IF EXISTS users_select_all ON users;

-- Policy permissiva: auth service gerencia segurança por conta própria
CREATE POLICY users_full_access ON users USING (true) WITH CHECK (true);
