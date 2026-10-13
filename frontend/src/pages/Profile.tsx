import { useAuth } from '../auth/AuthProvider';

export function Profile() {
  const { session, profile, signOut } = useAuth();
  return (
    <main className="page narrow">
      <h1>Profile</h1>
      <div className="card">
        <dl style={{ margin: 0 }}>
          <dt className="muted">Name</dt><dd style={{ margin: '0 0 12px' }}>{profile?.display_name || '—'}</dd>
          <dt className="muted">Email</dt><dd style={{ margin: '0 0 12px' }}>{session?.user.email}</dd>
          <dt className="muted">Role</dt><dd style={{ margin: 0 }}>{profile?.role ?? '—'}</dd>
        </dl>
        <p className="muted">Your role is set by an administrator and can't be changed here.</p>
        <button className="btn btn-secondary" onClick={() => void signOut()}>Sign out</button>
      </div>
    </main>
  );
}
