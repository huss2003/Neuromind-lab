import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { Loading } from '../components/States';
import { useAuth, type Role } from './AuthProvider';

export function RequireAuth({ roles }: { roles?: Role[] }) {
  const { loading, session, role } = useAuth();
  const location = useLocation();
  if (loading) return <Loading label="Checking your sign-in…" />; // protected content never flashes before this resolves
  if (!session) return <Navigate to="/sign-in" replace state={{ from: location.pathname }} />;
  if (roles && (!role || !roles.includes(role))) {
    return (
      <main className="page narrow">
        <h1>Not available</h1>
        <p role="alert">You don't have access to this page.</p>
      </main>
    );
  }
  return <Outlet />;
}
