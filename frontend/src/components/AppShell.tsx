import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../auth/AuthProvider';
import { BrandMark, BrandName } from './Brand';
import { Icon } from './Icon';

const initials = (s: string) => s.split(/[\s@.]+/).filter(Boolean).slice(0, 2).map((p) => p[0]?.toUpperCase()).join('') || 'N';

export function AppShell() {
  const { session, profile, role, signOut } = useAuth();
  const teacher = role === 'teacher' || role === 'admin';
  const learner = role === 'learner';
  const name = profile?.display_name || session?.user.email || '';
  return (
    <>
      <a className="skip-link" href="#main">Skip to content</a>
      <div className={`app${session ? '' : ' app-bare'}`}>
        <aside className="rail">
          <NavLink to="/" className="brand" aria-label="NeuroMind Lab home">
            <BrandMark size={34} />
            <BrandName />
          </NavLink>
          {session && (
            <nav className="sidenav" aria-label="Main">
              <NavLink to="/" end><Icon name="home" /> Dashboard</NavLink>
              <NavLink to="/progress"><Icon name="chart" /> My progress</NavLink>
              <NavLink to="/labs"><Icon name="code" /> Practical labs</NavLink>
              {learner && <NavLink to="/certificates"><Icon name="trophy" /> Certificates</NavLink>}
              {learner && <NavLink to="/portfolio"><Icon name="book" /> Portfolio</NavLink>}
              {teacher && <NavLink to="/teacher"><Icon name="book" /> Teacher</NavLink>}
              {role === 'admin' && <NavLink to="/admin"><Icon name="shield" /> Administration</NavLink>}
              <NavLink to="/profile"><Icon name="user" /> Profile</NavLink>
              <NavLink to="/help"><Icon name="info" /> Help</NavLink>
            </nav>
          )}
          {session && (
            <div className="rail-user">
              <span className="avatar" aria-hidden="true">{initials(name)}</span>
              <span className="user-name" title={session.user.email}>{name}</span>
              <button className="btn btn-quiet" onClick={() => void signOut()}><Icon name="logout" size={16} /> Sign out</button>
            </div>
          )}
        </aside>
        <div id="main" className="content" tabIndex={-1}>
          <Outlet />
        </div>
      </div>
    </>
  );
}
