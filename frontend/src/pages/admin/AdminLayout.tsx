import { NavLink, Outlet } from 'react-router-dom';

const LINKS: [string, string][] = [
  ['/admin', 'Overview'], ['/admin/users', 'Users'], ['/admin/cohorts', 'Cohorts'], ['/admin/content', 'Content'],
  ['/admin/queue', 'Grading queue'], ['/admin/audit', 'Audit log'], ['/admin/issues', 'Issue reports'], ['/admin/settings', 'Settings'],
];

export function AdminLayout() {
  return (
    <main className="page">
      <h1>Administration</h1>
      <nav className="subnav" aria-label="Administration sections">
        {LINKS.map(([to, label]) => <NavLink key={to} to={to} end={to === '/admin'}>{label}</NavLink>)}
      </nav>
      <Outlet />
    </main>
  );
}
