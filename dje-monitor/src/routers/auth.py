"""
Router de autenticação.

Endpoints públicos:
    POST /auth/login
    POST /auth/refresh
    POST /auth/logout

Endpoints autenticados:
    GET  /auth/me
    PATCH /auth/me/password
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from auth.auth_service import AuthenticationError, AccountLockedError
from auth.dependencies import get_current_user, CurrentUser
from schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    RefreshResponse,
    UserProfile,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

# Injetado pelo api.py
_auth_service = None
_rate_limiter = None


def set_auth_service(auth_service):
    global _auth_service
    _auth_service = auth_service


def set_rate_limiter(rate_limiter):
    global _rate_limiter
    _rate_limiter = rate_limiter


def get_auth_service():
    if _auth_service is None:
        raise RuntimeError("AuthService não inicializado.")
    return _auth_service


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, request: Request):
    """Login com email e senha. Retorna access + refresh tokens."""
    auth = get_auth_service()
    ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    if _rate_limiter:
        _rate_limiter.check(ip)
    try:
        result = auth.login(
            email=data.email,
            password=data.password,
            ip=ip,
            user_agent=user_agent,
        )
        return result
    except AccountLockedError as e:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(e))
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh", response_model=RefreshResponse)
def refresh_token(data: RefreshRequest):
    """Troca refresh token por novos access + refresh tokens (rotation)."""
    auth = get_auth_service()
    try:
        return auth.refresh(data.refresh_token)
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/logout")
def logout(data: RefreshRequest):
    """Revoga a sessão (toda a família de refresh tokens)."""
    auth = get_auth_service()
    auth.logout(data.refresh_token)
    return {"message": "Logout realizado"}


@router.get("/me", response_model=UserProfile)
def get_profile(
    user: CurrentUser = Depends(get_current_user),
    request: Request = None,
):
    """Retorna dados do usuário logado."""
    # Injetar repo pelo request.app.state ou via import global
    from api import repo
    from storage.models import User as UserModel

    with repo.get_session(user.tenant_id) as session:
        db_user = session.query(UserModel).filter(UserModel.id == user.user_id).first()
        if not db_user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        return UserProfile(
            id=str(db_user.id),
            name=db_user.name,
            email=db_user.email,
            role=db_user.role,
            tenant_id=str(db_user.tenant_id),
            last_login_at=db_user.last_login_at.isoformat() if db_user.last_login_at else None,
            must_change_password=db_user.must_change_password or False,
            created_at=db_user.created_at.isoformat() if db_user.created_at else "",
        )


@router.patch("/me/password")
def change_password(
    data: ChangePasswordRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Troca a própria senha. Requer senha atual."""
    auth = get_auth_service()
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="A nova senha deve ter pelo menos 8 caracteres.")
    try:
        auth.change_password(user.user_id, data.current_password, data.new_password)
        return {"message": "Senha alterada com sucesso"}
    except AuthenticationError as e:
        raise HTTPException(status_code=400, detail=str(e))
