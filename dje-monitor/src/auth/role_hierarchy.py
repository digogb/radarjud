"""Hierarquia de roles para gestão de usuários."""

from fastapi import HTTPException

ROLE_LEVEL = {
    "owner": 100,
    "admin": 80,
    "advogado": 50,
    "estagiario": 30,
    "leitura": 10,
}

VALID_ROLES = set(ROLE_LEVEL.keys())


def validate_role_hierarchy(actor_role: str, target_role: str) -> None:
    """
    Verifica se o actor pode atribuir/gerenciar o target_role.
    Um usuário só pode gerenciar roles de nível inferior ao seu.
    """
    actor_level = ROLE_LEVEL.get(actor_role, 0)
    target_level = ROLE_LEVEL.get(target_role, 0)

    if target_level >= actor_level:
        raise HTTPException(
            status_code=403,
            detail=f"Você ({actor_role}) não pode atribuir o role '{target_role}'",
        )


def can_manage_user(actor_role: str, target_role: str) -> bool:
    """Retorna True se actor_role pode gerenciar um usuário com target_role."""
    actor_level = ROLE_LEVEL.get(actor_role, 0)
    target_level = ROLE_LEVEL.get(target_role, 0)
    return actor_level > target_level
