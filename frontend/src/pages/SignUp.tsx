import { useState, type FormEvent } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthProvider';
import { BrandMark, BrandName } from '../components/Brand';
import { NeuralField } from '../components/NeuralField';
import { SIGNUP_ENABLED } from '../config';
import { supabase } from '../services/supabase';

/** Self-registration (only when the deployment enables it). The confirmation is identical whether or not the address is already registered,
 *  and the account cannot sign in until the emailed link has been used. Enrolment in a course is still done by a teacher or administrator. */
export function SignUp() {
  const { session } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [agree, setAgree] = useState(false);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resent, setResent] = useState(false);

  if (session) return <Navigate to="/" replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    const { error: err } = await supabase.auth.signUp({ email: email.trim(), password, options: { data: { display_name: name.trim() }, emailRedirectTo: `${window.location.origin}/sign-in` } });
    setBusy(false);
    if (err && /password|weak|short/i.test(err.message)) setError('That password is not accepted. Use at least 12 characters that are not easy to guess.');
    else if (err && /rate|too many/i.test(err.message)) setError('Too many attempts. Please wait a few minutes and try again.');
    else setDone(true); // any other outcome looks the same: no hint whether the address was already registered
  }

  return (
    <div className="auth-wrap">
      <a className="skip-link" href="#auth-main">Skip to content</a>
      <aside className="auth-aside">
        <NeuralField />
        <div className="auth-aside-copy">
          <div className="brand"><BrandMark size={40} /><BrandName /></div>
          <p className="auth-lede">Start learning Python.</p>
          <p className="auth-sub">Create an account, confirm your email, and your teacher can enrol you in a course.</p>
        </div>
      </aside>
      <main id="auth-main" className="auth-main" tabIndex={-1}>
        <div className="auth-card">
          <div className="brand auth-brand"><BrandMark size={32} /><BrandName /></div>
          {!SIGNUP_ENABLED ? (
            <>
              <h1>Create an account</h1>
              <div className="notice notice-info"><p>Accounts for this course are created by your teacher or administrator. Ask them to add you, then use <Link to="/sign-in">Sign in</Link>.</p></div>
            </>
          ) : done ? (
            <>
              <h1>Check your email</h1>
              <div role="status" className="notice notice-success">
                <p>If that address can be registered, we have sent a confirmation link to it. Open the link, then sign in. The link works for a limited time.</p>
              </div>
              <button className="btn btn-secondary" disabled={resent} onClick={() => { void supabase.auth.resend({ type: 'signup', email: email.trim() }); setResent(true); }}>{resent ? 'Sent again' : 'Send the email again'}</button>
              <p><Link to="/sign-in">Back to sign in</Link></p>
            </>
          ) : (
            <>
              <h1>Create an account</h1>
              <form onSubmit={onSubmit}>
                <label htmlFor="su-name">Full name</label>
                <input id="su-name" type="text" required maxLength={80} autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} />
                <label htmlFor="su-email">Email</label>
                <input id="su-email" type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
                <label htmlFor="su-pass">Password</label>
                <input id="su-pass" type="password" required minLength={12} maxLength={128} autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} aria-describedby="su-pass-h" />
                <p id="su-pass-h" className="field-hint">At least 12 characters.</p>
                <label className="check-row"><input type="checkbox" required checked={agree} onChange={(e) => setAgree(e.target.checked)} /> I have read the <Link to="/privacy" target="_blank">privacy notice</Link> and <Link to="/terms" target="_blank">terms of use</Link>.</label>
                {error && <p role="alert" className="field-error">{error}</p>}
                <div className="actions"><button type="submit" className="btn btn-primary btn-block" disabled={busy || !agree}>{busy ? 'Creating…' : 'Create account'}</button></div>
              </form>
              <p><Link to="/sign-in">I already have an account</Link></p>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
