import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Permission, hasPermission, UserRole } from '../lib/permissions';

interface Props {
  children: React.ReactNode;
  permission?: Permission;
}

export function ProtectedRoute({ children, permission }: Props) {
  const { isAuthenticated, user, isLoading } = useAuth();

  if (isLoading) {
    return <div style={{ padding: '2rem', textAlign: 'center', color: '#94a3b8' }}>Carregando...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (permission && user && !hasPermission(user.role as UserRole, permission)) {
    return <Navigate to="/403" replace />;
  }

  return <>{children}</>;
}
