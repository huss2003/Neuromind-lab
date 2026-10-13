import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { BrandMark, BrandName } from '../components/Brand';
import { NeuralField } from '../components/NeuralField';
import { supabase } from '../services/supabase';

/** S02 — always shows the same confirmation so the page never reveals whether an account exists. */
export function Recover() {
  const [email, setEmail] = useState('');
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    try {
      await supabase.auth.resetPasswordForEmail(email.trim(), { redirectTo: `${window.location.origin}/sign-in` });
    } catch {
      /* deliberately ignored: the response must not depend on the outcome */
    }
    setBusy(false);
    setSent(true);
  }

  return (
    <div className="auth-wrap">
      <aside className="auth-aside">
        <NeuralField />
        <div className="auth-aside-copy">
          <div className="brand"><BrandMark size={40} /><BrandName /></div>
          <p className="auth-lede">Locked out? It happens.</p>
          <p className="auth-sub">Tell us your email and we will send you a way back in. Your progress is waiting.</p>
        </div>
      </aside>
      <main className="auth-main">
      <div className="auth-card">
        <div className="brand auth-brand"><BrandMark size={32} /><BrandName /></div>
        <h1>Recover your account</h1>
        {sent ? (
          <>
            <div role="status" className="notice notice-info">
              If an account exists for that email, we have sent instructions to it. Check your inbox and spam folder. It can take a few minutes.
            </div>
            <p className="muted">Didn’t get anything? Wait a few minutes before you try again.</p>
            <div className="actions">
              <button className="btn btn-secondary" onClick={() => setSent(false)}>Try a different email</button>
              <Link className="btn btn-primary" to="/sign-in">Return to sign in</Link>
            </div>
          </>
        ) : (
          <form onSubmit={onSubmit}>
            <p className="muted">Enter the email you use for NeuroMind Lab. We will send reset instructions if an account exists.</p>
            <label htmlFor="recover-email">Email</label>
            <input id="recover-email" type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            <div className="actions">
              <button type="submit" className="btn btn-primary" disabled={busy} style={{ width: '100%' }}>{busy ? 'Sending…' : 'Send reset instructions'}</button>
            </div>
            <p><Link to="/sign-in">Back to sign in</Link></p>
          </form>
        )}
      </div>
      </main>
    </div>
  );
}
