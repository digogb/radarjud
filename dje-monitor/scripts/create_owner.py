#!/usr/bin/env python3
"""
Script para criar o primeiro usuário (owner) de um tenant.

Uso:
    python scripts/create_owner.py \
        --tenant-slug silva-associados \
        --email admin@silva.adv.br \
        --name "Dr. Silva" \
        --password "SenhaSegura123"

Ou sem --password para gerar uma senha aleatória.
"""

import argparse
import os
import secrets
import string
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from storage.models import Tenant, User
from auth.password import hash_password


def generate_password(length: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def create_owner(slug: str, email: str, name: str, password: str | None = None) -> None:
    database_url = os.getenv("DJE_DATABASE_URL")
    if not database_url:
        print("ERRO: DJE_DATABASE_URL não configurado.")
        sys.exit(1)

    engine = create_engine(database_url, echo=False)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        # Buscar tenant pelo slug (sem RLS)
        tenant = session.query(Tenant).filter(Tenant.slug == slug).first()
        if not tenant:
            print(f"ERRO: Tenant com slug '{slug}' não encontrado.")
            print("Tenants disponíveis:")
            for t in session.query(Tenant).all():
                print(f"  - {t.slug} ({t.name}) id={t.id}")
            sys.exit(1)

        if not tenant.is_active:
            print(f"AVISO: Tenant '{slug}' está desativado.")

        # Verificar se já existe um owner
        existing_owner = session.query(User).filter(
            User.tenant_id == tenant.id,
            User.role == "owner",
        ).first()
        if existing_owner:
            print(f"AVISO: Já existe um owner para este tenant: {existing_owner.email}")
            confirm = input("Criar outro owner mesmo assim? [s/N]: ").strip().lower()
            if confirm != "s":
                print("Cancelado.")
                return

        # Verificar se email já existe
        existing_email = session.query(User).filter(
            User.tenant_id == tenant.id,
            User.email == email,
        ).first()
        if existing_email:
            print(f"ERRO: Email '{email}' já cadastrado neste tenant.")
            sys.exit(1)

        # Gerar senha se não fornecida
        generated = False
        if not password:
            password = generate_password()
            generated = True

        user = User(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            email=email,
            name=name,
            password_hash=hash_password(password),
            role="owner",
            is_active=True,
            must_change_password=generated,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(user)
        session.commit()

        print(f"\n✓ Owner criado com sucesso!")
        print(f"  Tenant : {tenant.name} ({tenant.slug})")
        print(f"  Email  : {email}")
        print(f"  Nome   : {name}")
        print(f"  Role   : owner")
        if generated:
            print(f"  Senha  : {password}  ← ANOTE AGORA, não será exibida novamente!")
            print(f"  Obs    : Usuário deverá trocar a senha no primeiro login.")
        else:
            print(f"  Senha  : (definida pelo usuário)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Criar owner de um tenant")
    parser.add_argument("--tenant-slug", required=True, help="Slug do tenant")
    parser.add_argument("--email", required=True, help="Email do owner")
    parser.add_argument("--name", required=True, help="Nome completo do owner")
    parser.add_argument("--password", help="Senha (omitir para gerar automaticamente)")
    args = parser.parse_args()

    create_owner(
        slug=args.tenant_slug,
        email=args.email,
        name=args.name,
        password=args.password,
    )
