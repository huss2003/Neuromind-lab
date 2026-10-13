import { useState, type FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthProvider';
import { supabase } from '../services/supabase';

export function SignIn() {
  const navigate = useNavigate();
  const location = useLocation();
  const { session, expired } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [show, setShow] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const from = (location.state as { from?: string } | null)?.from ?? '/';

  if (session) return <Navigate to={from} replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    const { error: err } = await supabase.auth.signInWithPassword({ email: email.trim(), password });
    setBusy(false);
    if (err) setError('Sign-in failed. Check your email and password, then try again.'); // generic: never reveals which part was wrong
    else navigate(from, { replace: true });
  }

  return (
    <div className="auth-wrap">
      <main className="auth-card">
        <div className="brand"><span className="brand-mark" aria-hidden="true">N</span><span>NeuroMind <strong>Lab</strong></span></div>
        <h1>Sign in</h1>
        <p className="muted">Practise Python, answer checkpoints and see your progress.</p>
        {expired && <div role="status" className="notice notice-warning">Your session ended. Please sign in again — your saved progress is safe.</div>}
        <form onSubmit={onSubmit} noValidate={false} aria-describedby={error ? 'signin-error' : undefined}>
          <label htmlFor="email">Email</label>
          <input id="email" type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} aria-invalid={error ? true : undefined} />
          <label htmlFor="password">Password</label>
          <div className="pw-row">
            <input id="password" type={show ? 'text' : 'password'} required autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} aria-invalid={error ? true : undefined} />
            <button type="button" className="btn btn-tertiary pw-toggle" onClick={() => setShow((v) => !v)} aria-pressed={show}>{show ? 'Hide' : 'Show'}</button>
          </div>
          {error && <p id="signin-error" role="alert" className="field-error">{error}</p>}
          <div className="actions">
            <button type="submit" className="btn btn-primary" disabled={busy} style={{ width: '100%' }}>{busy ? 'Signing in…' : 'Sign in'}</button>
          </div>
        </form>
      </main>
    </div>
  );
}
