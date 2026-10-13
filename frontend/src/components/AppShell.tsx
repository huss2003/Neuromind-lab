import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../auth/AuthProvider';
import { Icon } from './Icon';

export function AppShell() {
  const { session, profile, role, signOut } = useAuth();
  const teacher = role === 'teacher' || role === 'admin';
  const name = profile?.display_name || session?.user.email || '';
  return (
    <>
      <a className="skip-link" href="#main">Skip to content</a>
      <header className="topbar">
        <NavLink to="/" className="brand" aria-label="NeuroMind Lab home">
          <span className="brand-mark" aria-hidden="true">N</span>
          <span>NeuroMind <strong>Lab</strong></span>
        </NavLink>
        {session && (
          <div className="topbar-user">
            <span className="user-name" title={session.user.email}>{name}</span>
            <button className="btn btn-tertiary" onClick={() => void signOut()}><Icon name="logout" size={16} /> Sign out</button>
          </div>
        )}
      </header>
      <div className="shell">
        {session && (
          <nav className="sidenav" aria-label="Main">
            <NavLink to="/" end><Icon name="home" /> Dashboard</NavLink>
            <NavLink to="/progress"><Icon name="chart" /> My progress</NavLink>
            {teacher && <NavLink to="/teacher"><Icon name="book" /> Teacher</NavLink>}
            <NavLink to="/profile"><Icon name="user" /> Profile</NavLink>
          </nav>
        )}
        <div id="main" className="content" tabIndex={-1}>
          <Outlet />
        </div>
      </div>
    </>
  );
}
