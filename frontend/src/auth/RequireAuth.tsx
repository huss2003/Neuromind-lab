import { Navigate, Outlet } from 'react-router-dom';
import { Loading } from '../components/States';
import { useAuth, type Role } from './AuthProvider';

export function RequireAuth({ roles }: { roles?: Role[] }) {
  const { loading, session, role } = useAuth();
  if (loading) return <Loading label="Checking your sign-in…" />;
  if (!session) return <Navigate to="/sign-in" replace />;
  if (roles && (!role || !roles.includes(role))) {
    return <main><h1>Not available</h1><p role="alert">You don't have access to this page.</p></main>;
  }
  return <Outlet />;
}
