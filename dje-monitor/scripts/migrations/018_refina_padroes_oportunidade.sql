-- Migration 018: refina padrões de oportunidade (por tenant)
--
-- Motivo: negativos genéricos ("extinção", "suspensão", "rescisão") invalidavam
-- processos que na verdade tinham sinal de crédito:
--   - "extinção da execução pelo pagamento" (art. 924, II CPC) = crédito recebido
--   - "suspensão por acordo de parcelamento" = recebimento futuro
--   - "rescisão" casava por substring com "ação rescisória" (irrelevante)
--
-- Rodar como superuser `dje` (bypassa RLS) para atingir todos os tenants:
--   docker exec -i dje-monitor-postgres psql -U dje -d dje_monitor < 018_refina_padroes_oportunidade.sql
--
-- Idempotente: pode ser reexecutada sem duplicar linhas.

BEGIN;

-- 1. Remover negativos genéricos demais.
DELETE FROM padroes_oportunidade
WHERE tipo = 'negativo'
  AND lower(expressao) IN ('extinção', 'suspensão', 'rescisão');

-- 2. Inserir negativos específicos por tenant (só se ainda não existirem).
INSERT INTO padroes_oportunidade (tenant_id, nome, expressao, tipo, ativo, ordem, criado_em)
SELECT DISTINCT tids.tenant_id, novos.nome, novos.expressao, 'negativo', true, 90, now()
FROM (SELECT DISTINCT tenant_id FROM padroes_oportunidade) tids
CROSS JOIN (VALUES
    ('Extinção sem mérito', 'extinção sem resolução'),
    ('Improcedência',       'improcedência')
) AS novos(nome, expressao)
WHERE NOT EXISTS (
    SELECT 1 FROM padroes_oportunidade p
    WHERE p.tenant_id IS NOT DISTINCT FROM tids.tenant_id
      AND lower(p.expressao) = lower(novos.expressao)
);

-- 3. Inserir positivo "extinção pelo pagamento" por tenant (só se ainda não existir).
INSERT INTO padroes_oportunidade (tenant_id, nome, expressao, tipo, ativo, ordem, criado_em)
SELECT DISTINCT tids.tenant_id, novos.nome, novos.expressao, 'positivo', true, 90, now()
FROM (SELECT DISTINCT tenant_id FROM padroes_oportunidade) tids
CROSS JOIN (VALUES
    ('Extinção pelo Pagamento', 'extinção da execução pelo pagamento'),
    ('Extinção pelo Pagamento', 'extinta a execução pelo pagamento')
) AS novos(nome, expressao)
WHERE NOT EXISTS (
    SELECT 1 FROM padroes_oportunidade p
    WHERE p.tenant_id IS NOT DISTINCT FROM tids.tenant_id
      AND lower(p.expressao) = lower(novos.expressao)
);

COMMIT;
