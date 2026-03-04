"""
Permissões por role no DJE Monitor.

Matriz de permissões:
Permissão                    owner   admin   advogado   estagiario   leitura
─────────────────────────────────────────────────────────────────────────────
Visualizar processos          ✓       ✓        ✓           ✓           ✓
Busca semântica               ✓       ✓        ✓           ✓           ✓
Cadastrar processo            ✓       ✓        ✓           ✓           ✗
Editar processo               ✓       ✓        ✓           ✗           ✗
Excluir processo              ✓       ✓        ✗           ✗           ✗
Gerenciar usuários            ✓       ✓        ✗           ✗           ✗
Alterar roles                 ✓       ✓*       ✗           ✗           ✗
Configurações do tenant       ✓       ✗        ✗           ✗           ✗
Ver audit log                 ✓       ✓        ✗           ✗           ✗
Exportar dados                ✓       ✓        ✓           ✗           ✗

* admin pode alterar roles de advogado/estagiario/leitura, mas não de outros admins
"""

from enum import Enum


class Permission(str, Enum):
    PROCESSOS_VIEW = "processos:view"
    PROCESSOS_CREATE = "processos:create"
    PROCESSOS_EDIT = "processos:edit"
    PROCESSOS_DELETE = "processos:delete"
    SEARCH_SEMANTIC = "search:semantic"
    USERS_MANAGE = "users:manage"
    USERS_ROLES = "users:roles"
    TENANT_SETTINGS = "tenant:settings"
    AUDIT_VIEW = "audit:view"
    DATA_EXPORT = "data:export"


ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    "owner": set(Permission),  # Tudo
    "admin": {
        Permission.PROCESSOS_VIEW,
        Permission.PROCESSOS_CREATE,
        Permission.PROCESSOS_EDIT,
        Permission.PROCESSOS_DELETE,
        Permission.SEARCH_SEMANTIC,
        Permission.USERS_MANAGE,
        Permission.USERS_ROLES,
        Permission.AUDIT_VIEW,
        Permission.DATA_EXPORT,
    },
    "advogado": {
        Permission.PROCESSOS_VIEW,
        Permission.PROCESSOS_CREATE,
        Permission.PROCESSOS_EDIT,
        Permission.SEARCH_SEMANTIC,
        Permission.DATA_EXPORT,
    },
    "estagiario": {
        Permission.PROCESSOS_VIEW,
        Permission.PROCESSOS_CREATE,
        Permission.SEARCH_SEMANTIC,
    },
    "leitura": {
        Permission.PROCESSOS_VIEW,
        Permission.SEARCH_SEMANTIC,
    },
}


def has_permission(role: str, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
