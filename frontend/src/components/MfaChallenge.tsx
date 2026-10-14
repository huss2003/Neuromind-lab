import { useEffect, useState, type FormEvent } from 'react';
import { useAuth } from '../auth/AuthProvider';
import { supabase } from '../services/supabase';

/** Second step of sign-in for accounts that turned on two-step verification. The API also refuses a token that has not completed this step. */
export function MfaChallenge() {
  const { signOut, refreshAssurance } = useAuth();
  const [factorId, setFactorId] = useState<string | null>(null);
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void supabase.auth.mfa.listFactors().then(({ data }) => setFactorId(data?.totp.find((f) => f.status === 'verified')?.id ?? null));
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!factorId || busy) return;
    setBusy(true);
    setError(null);
    const { error: err } = await supabase.auth.mfa.challengeAndVerify({ factorId, code: code.replace(/\s/g, '') });
    setBusy(false);
    if (err) { setError('That code did not work. Check the code in your authenticator app and try again.'); setCode(''); } else await refreshAssurance();
  }

  return (
    <main className="page narrow">
      <h1>Two-step verification</h1>
      <p>Open your authenticator app and enter the 6-digit code for NeuroMind Lab.</p>
      <form onSubmit={onSubmit}>
        <label htmlFor="mfa-code">6-digit code</label>
        <input id="mfa-code" type="text" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9 ]{6,7}" required value={code} onChange={(e) => setCode(e.target.value)} aria-invalid={error ? true : undefined} style={{ maxWidth: 200 }} autoFocus />
        {error && <p role="alert" className="field-error">{error}</p>}
        <div className="actions">
          <button className="btn btn-primary" type="submit" disabled={busy || !factorId || code.replace(/\s/g, '').length < 6}>{busy ? 'Checking…' : 'Verify'}</button>
          <button className="btn btn-tertiary" type="button" onClick={() => void signOut()}>Sign out</button>
        </div>
      </form>
    </main>
  );
}
