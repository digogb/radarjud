"""Schemas Pydantic para o recurso Tenant."""

import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    slug: str = Field(..., min_length=3, max_length=100)
    settings: dict = Field(default_factory=dict)

    @field_validator("slug")
    @classmethod
    def slug_must_be_valid(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError("slug deve conter apenas letras minúsculas, números e hífens")
        return v


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    settings: Optional[dict] = None
    is_active: Optional[bool] = None


class TenantResponse(BaseModel):
    id: str
    name: str
    slug: str
    is_active: bool
    settings: dict
    created_at: str

    @classmethod
    def from_orm(cls, tenant) -> "TenantResponse":
        return cls(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            is_active=tenant.is_active,
            settings=tenant.settings or {},
            created_at=tenant.created_at.isoformat() if tenant.created_at else "",
        )


class TenantWithStats(TenantResponse):
    total_pessoas: int = 0
    total_publicacoes: int = 0
    total_alertas_nao_lidos: int = 0
    ultima_sync: Optional[str] = None
