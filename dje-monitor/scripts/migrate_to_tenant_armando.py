#!/usr/bin/env python3
"""
Script de migração: dados existentes → tenant "armando".

Execução:
    cd dje-monitor
    python scripts/migrate_to_tenant_armando.py

O script:
1. Cria o tenant "armando" no banco (ou reutiliza se já existe)
2. Executa a migration SQL 001 (adiciona tenant_id nas tabelas se necessário)
3. Faz UPDATE em todas as tabelas para setar tenant_id = armando.id
4. Torna tenant_id NOT NULL (executa migration SQL 003)
5. Cria as collections Qdrant para o tenant "armando"
6. Migra vetores das collections globais para as collections do tenant
7. (Opcional) Ativa RLS — executa migration SQL 002

IMPORTANTE: Rodar este script como superuser (não como app_user),
pois ele altera o schema (NOT NULL) e faz updates em massa.
"""

import os
import sys
import logging

# Garante imports do src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("migrate_armando")


def _exec_sql_file(conn, path: str, logger):
    """Executa arquivo SQL linha a linha, pulando comentários e usando SAVEPOINT por stmt."""
    import re
    sql = open(path).read()
    # Remove linhas de comentário e junta o resto
    stmts = []
    current = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--") or not stripped:
            continue
        current.append(line)
        if stripped.endswith(";"):
            stmt = " ".join(current).strip().rstrip(";")
            if stmt:
                stmts.append(stmt)
            current = []

    for stmt in stmts:
        try:
            conn.execute(text("SAVEPOINT sp1"))
            conn.execute(text(stmt))
            conn.execute(text("RELEASE SAVEPOINT sp1"))
        except Exception as e:
            conn.execute(text("ROLLBACK TO SAVEPOINT sp1"))
            logger.warning(f"  stmt ignorado (pode já existir): {stmt[:60]}... — {e}")


def run():
    from config import Config
    from sqlalchemy import create_engine, text
    from storage.models import Base, Tenant

    cfg = Config()
    engine = create_engine(cfg.database_url, echo=False)

    # ──────────────────────────────────────────────
    # 1. Garantir que a tabela tenants existe
    # ──────────────────────────────────────────────
    logger.info("Criando tabelas (se não existirem)...")
    Base.metadata.create_all(engine)

    # ──────────────────────────────────────────────
    # 2. Executar migration 001 (adicionar tenant_id)
    # ──────────────────────────────────────────────
    migration_001 = os.path.join(os.path.dirname(__file__), "migrations", "001_add_tenant_id.sql")
    if os.path.exists(migration_001):
        logger.info("Executando migration 001_add_tenant_id.sql...")
        with engine.connect() as conn:
            _exec_sql_file(conn, migration_001, logger)
            conn.commit()
        logger.info("Migration 001 concluída.")

    # ──────────────────────────────────────────────
    # 3. Criar (ou reutilizar) tenant "armando"
    # ──────────────────────────────────────────────
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)

    with Session() as session:
        existing = session.execute(
            text("SELECT id FROM tenants WHERE slug = 'armando' LIMIT 1")
        ).fetchone()

        if existing:
            armando_id = existing[0]
            logger.info(f"Tenant 'armando' já existe: {armando_id}")
        else:
            import uuid
            armando_id = str(uuid.uuid4())
            from datetime import datetime
            session.execute(
                text(
                    "INSERT INTO tenants (id, name, slug, is_active, settings, created_at, updated_at) "
                    "VALUES (:id, :name, :slug, true, '{}', :now, :now)"
                ),
                {
                    "id": armando_id,
                    "name": "Armando",
                    "slug": "armando",
                    "now": datetime.utcnow(),
                },
            )
            session.commit()
            logger.info(f"Tenant 'armando' criado com ID: {armando_id}")

    # ──────────────────────────────────────────────
    # 4. UPDATE em todas as tabelas
    # ──────────────────────────────────────────────
    tabelas = [
        "cpfs_monitorados",
        "diarios_processados",
        "ocorrencias",
        "pessoas_monitoradas",
        "publicacoes_monitoradas",
        "padroes_oportunidade",
        "classificacoes_processo",
        "oportunidades_descartadas",
        "alertas",
    ]

    with Session() as session:
        for tabela in tabelas:
            try:
                result = session.execute(
                    text(f"UPDATE {tabela} SET tenant_id = :tid WHERE tenant_id IS NULL"),
                    {"tid": armando_id},
                )
                session.commit()
                logger.info(f"  {tabela}: {result.rowcount} linha(s) atualizada(s)")
            except Exception as e:
                logger.warning(f"  {tabela}: erro no UPDATE (tabela pode não ter tenant_id ainda): {e}")
                session.rollback()

    # ──────────────────────────────────────────────
    # 5. Tornar tenant_id NOT NULL
    # ──────────────────────────────────────────────
    migration_003 = os.path.join(os.path.dirname(__file__), "migrations", "003_not_null_tenant_id.sql")
    if os.path.exists(migration_003):
        logger.info("Executando migration 003_not_null_tenant_id.sql...")
        with engine.connect() as conn:
            _exec_sql_file(conn, migration_003, logger)
            conn.commit()
        logger.info("Migration 003 concluída.")

    # ──────────────────────────────────────────────
    # 6. Criar collections Qdrant para "armando"
    # ──────────────────────────────────────────────
    logger.info("Criando collections Qdrant para tenant 'armando'...")
    try:
        from services.qdrant_tenant import ensure_tenant_collections, migrate_global_to_tenant
        ensure_tenant_collections(armando_id)
        logger.info("Collections Qdrant criadas.")

        # 7. Migrar vetores das collections globais
        logger.info("Migrando vetores das collections globais...")
        counts = migrate_global_to_tenant(armando_id)
        logger.info(f"Migração Qdrant concluída: {counts}")
    except Exception as e:
        logger.warning(f"Erro ao migrar Qdrant (pode ser ignorado se Qdrant não está acessível): {e}")

    logger.info("=" * 60)
    logger.info(f"MIGRAÇÃO CONCLUÍDA — Tenant ID: {armando_id}")
    logger.info("Próximos passos:")
    logger.info("  1. Configure DJE_TENANT_ID no .env ou passe X-Tenant-ID nas requests")
    logger.info("  2. (Opcional) Execute 002_rls_setup.sql para ativar RLS")
    logger.info("  3. Verifique: GET /health (sem tenant) e GET /api/v1/pessoas-monitoradas (com tenant)")
    logger.info(f"  Tenant ID: {armando_id}")
    logger.info("=" * 60)

    return armando_id


if __name__ == "__main__":
    run()
