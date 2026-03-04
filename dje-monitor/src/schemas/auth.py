"""Pydantic schemas para autenticação."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class UserInfo(BaseModel):
    id: str
    name: str
    email: str
    role: str
    tenant_id: str
    tenant_name: str
    must_change_password: bool = False


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserProfile(BaseModel):
    id: str
    name: str
    email: str
    role: str
    tenant_id: str
    last_login_at: Optional[str] = None
    must_change_password: bool = False
    created_at: str

    model_config = {"from_attributes": True}
