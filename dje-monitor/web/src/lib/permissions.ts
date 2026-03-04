/**
 * Permissões do frontend espelhando o backend (auth/permissions.py).
 * Usado para ocultar/mostrar elementos de UI com base no role do usuário.
 */

export type UserRole = 'owner' | 'admin' | 'advogado' | 'estagiario' | 'leitura';

export enum Permission {
  PROCESSOS_VIEW = 'processos:view',
  PROCESSOS_CREATE = 'processos:create',
  PROCESSOS_EDIT = 'processos:edit',
  PROCESSOS_DELETE = 'processos:delete',
  SEARCH_SEMANTIC = 'search:semantic',
  USERS_MANAGE = 'users:manage',
  USERS_ROLES = 'users:roles',
  TENANT_SETTINGS = 'tenant:settings',
  AUDIT_VIEW = 'audit:view',
  DATA_EXPORT = 'data:export',
}

const ROLE_PERMISSIONS: Record<UserRole, Set<Permission>> = {
  owner: new Set(Object.values(Permission)),
  admin: new Set([
    Permission.PROCESSOS_VIEW,
    Permission.PROCESSOS_CREATE,
    Permission.PROCESSOS_EDIT,
    Permission.PROCESSOS_DELETE,
    Permission.SEARCH_SEMANTIC,
    Permission.USERS_MANAGE,
    Permission.USERS_ROLES,
    Permission.AUDIT_VIEW,
    Permission.DATA_EXPORT,
  ]),
  advogado: new Set([
    Permission.PROCESSOS_VIEW,
    Permission.PROCESSOS_CREATE,
    Permission.PROCESSOS_EDIT,
    Permission.SEARCH_SEMANTIC,
    Permission.DATA_EXPORT,
  ]),
  estagiario: new Set([
    Permission.PROCESSOS_VIEW,
    Permission.PROCESSOS_CREATE,
    Permission.SEARCH_SEMANTIC,
  ]),
  leitura: new Set([
    Permission.PROCESSOS_VIEW,
    Permission.SEARCH_SEMANTIC,
  ]),
};

export function hasPermission(role: UserRole, permission: Permission): boolean {
  return ROLE_PERMISSIONS[role]?.has(permission) ?? false;
}
