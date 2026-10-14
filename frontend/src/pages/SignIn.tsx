import { useState, type FormEvent } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthProvider';
import { BrandMark, BrandName } from '../components/Brand';
import { NeuralField } from '../components/NeuralField';
import { OAUTH_PROVIDERS, SIGNUP_ENABLED } from '../config';
import { supabase } from '../services/supabase';

export function SignIn() {
  const navigate = useNavigate();
  const location = useLocation();
  const { session, expired, deactivated } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [show, setShow] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [unconfirmed, setUnconfirmed] = useState(false);
  const [resent, setResent] = useState(false);
  const from = (location.state as { from?: string } | null)?.from ?? '/';

  if (session) return <Navigate to={from} replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    const { error: err } = await supabase.auth.signInWithPassword({ email: email.trim(), password });
    setBusy(false);
    if (err && /not confirmed/i.test(err.message)) { setUnconfirmed(true); setError('Please confirm your email first. We sent you a link when you registered.'); } // only shown after a correct password
    else if (err) setError('Sign-in failed. Check your email and password, then try again.'); // generic: never reveals which part was wrong
    else navigate(from, { replace: true });
  }

  return (
    <div className="auth-wrap">
      <a className="skip-link" href="#auth-main">Skip to content</a>
      <aside className="auth-aside">
        <NeuralField />
        <div className="auth-aside-copy">
          <div className="brand"><BrandMark size={40} /><BrandName /></div>
          <p className="auth-lede">Learn Python by writing it.</p>
          <p className="auth-sub">Short lessons, real code, and grading you can trust. Your work is saved as you go, and help is one click away.</p>
        </div>
      </aside>
      <main id="auth-main" className="auth-main" tabIndex={-1}>
        <div className="auth-card">
          <div className="brand auth-brand"><BrandMark size={32} /><BrandName /></div>
          <h1>Sign in</h1>
          <p className="muted">Pick up where you left off.</p>
          {deactivated && <div role="alert" className="notice notice-warning">This account has been deactivated. Contact your course administrator.</div>}
          {expired && <div role="status" className="notice notice-warning">Your session ended. Please sign in again — your saved progress is safe.</div>}
          <form onSubmit={onSubmit} noValidate={false} aria-describedby={error ? 'signin-error' : undefined}>
            <label htmlFor="email">Email</label>
            <input id="email" type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} aria-invalid={error ? true : undefined} />
            <label htmlFor="password">Password</label>
            <div className="pw-row">
              <input id="password" type={show ? 'text' : 'password'} required autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} aria-invalid={error ? true : undefined} />
              <button type="button" className="btn btn-quiet pw-toggle" onClick={() => setShow((v) => !v)} aria-pressed={show}>{show ? 'Hide' : 'Show'}</button>
            </div>
            {error && <p id="signin-error" role="alert" className="field-error">{error}</p>}
            <div className="actions">
              <button type="submit" className="btn btn-primary btn-block" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
            </div>
            {unconfirmed && <p><button type="button" className="btn btn-secondary" disabled={resent} onClick={() => { void supabase.auth.resend({ type: 'signup', email: email.trim() }); setResent(true); }}>{resent ? 'Sent again' : 'Send the confirmation email again'}</button></p>}
            <p><Link to="/recover">Forgot your password?</Link></p>
          </form>
          {OAUTH_PROVIDERS.length > 0 && (
            <div className="oauth" role="group" aria-label="Other ways to sign in">
              <p className="muted">or continue with</p>
              {OAUTH_PROVIDERS.map((p) => (
                <button key={p} type="button" className="btn btn-secondary btn-block" onClick={() => void supabase.auth.signInWithOAuth({ provider: p as 'google', options: { redirectTo: `${window.location.origin}/` } })}>
                  {p.charAt(0).toUpperCase() + p.slice(1)}
                </button>
              ))}
            </div>
          )}
          {SIGNUP_ENABLED && <p>New here? <Link to="/sign-up">Create an account</Link></p>}
          <p className="muted auth-legal"><Link to="/policies">Policies</Link> · <Link to="/privacy">Privacy</Link> · <Link to="/terms">Terms</Link></p>
        </div>
      </main>
    </div>
  );
}
