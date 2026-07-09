-- Migration 017: coluna de controle da primeira varredura de oportunidades por pessoa
-- NULL = pessoa ainda não teve a 1ª varredura → alerta o histórico inteiro (sem janela de 7d).
-- Depois de varrida, as próximas varreduras usam a janela normal de 7 dias.

ALTER TABLE pessoas_monitoradas
    ADD COLUMN IF NOT EXISTS oportunidades_varridas_em TIMESTAMP NULL;
