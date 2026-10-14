import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthProvider';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { supabase } from '../services/supabase';

interface Enrolment { factorId: string; qr: string; secret: string }

/** Optional two-step verification (an authenticator app). Once on, sign-in needs the code, and the API refuses a session that skipped it. */
function TwoStep() {
  const qc = useQueryClient();
  const { refreshAssurance } = useAuth();
  const factors = useQuery({ queryKey: ['mfa-factors'], queryFn: async () => (await supabase.auth.mfa.listFactors()).data?.totp ?? [] });
  const [enrol, setEnrol] = useState<Enrolment | null>(null);
  const [code, setCode] = useState('');
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');
  const [confirmOff, setConfirmOff] = useState<string | null>(null);
  const verified = factors.data?.find((f) => f.status === 'verified');

  async function start() {
    setError(''); setMsg('');
    await supabase.auth.mfa.listFactors().then(async ({ data }) => { for (const f of data?.totp ?? []) if (f.status !== 'verified') await supabase.auth.mfa.unenroll({ factorId: f.id }); }); // clear abandoned attempts
    const { data, error: err } = await supabase.auth.mfa.enroll({ factorType: 'totp', friendlyName: 'Authenticator app' });
    if (err || !data) { setError('Could not start setup. Please try again.'); return; }
    setEnrol({ factorId: data.id, qr: data.totp.qr_code, secret: data.totp.secret });
  }
  async function confirm(e: FormEvent) {
    e.preventDefault();
    if (!enrol) return;
    const { error: err } = await supabase.auth.mfa.challengeAndVerify({ factorId: enrol.factorId, code: code.replace(/\s/g, '') });
    if (err) { setError('That code did not match. Check the code in your app and try again.'); setCode(''); return; }
    setEnrol(null); setCode(''); setMsg('Two-step verification is on. You will be asked for a code each time you sign in.');
    await refreshAssurance(); void qc.invalidateQueries({ queryKey: ['mfa-factors'] });
  }
  async function turnOff(id: string) {
    const { error: err } = await supabase.auth.mfa.unenroll({ factorId: id });
    setConfirmOff(null);
    if (err) { setError('Could not turn it off. Sign in again and retry.'); return; }
    setMsg('Two-step verification is off.'); void qc.invalidateQueries({ queryKey: ['mfa-factors'] });
  }

  return (
    <section className="card" aria-labelledby="mfa-h">
      <h2 id="mfa-h" style={{ marginTop: 0 }}>Two-step verification</h2>
      {msg && <div role="status" className="notice notice-success"><p>{msg}</p></div>}
      {error && <p role="alert" className="field-error">{error}</p>}
      {factors.isPending && <p role="status">Checking…</p>}
      {verified && !enrol && (
        <>
          <p>It is <strong>on</strong>. You use an authenticator app to sign in.</p>
          <button className="btn btn-secondary" onClick={() => setConfirmOff(verified.id)}>Turn off</button>
        </>
      )}
      {factors.data && !verified && !enrol && (
        <>
          <p>Add a second step to sign-in with an authenticator app (such as Google Authenticator, Microsoft Authenticator or 1Password). It is optional, and recommended for teachers and administrators.</p>
          <button className="btn btn-primary" onClick={() => void start()}>Set up</button>
        </>
      )}
      {enrol && (
        <form onSubmit={confirm}>
          <ol>
            <li>Scan this image with your authenticator app. <img src={enrol.qr} alt="QR code for your authenticator app" width={180} height={180} style={{ display: 'block', background: '#fff', padding: 8, margin: '8px 0' }} /></li>
            <li>Cannot scan? Enter this key by hand: <code>{enrol.secret}</code></li>
            <li>Type the 6-digit code the app shows.</li>
          </ol>
          <label htmlFor="mfa-setup-code">6-digit code</label>
          <input id="mfa-setup-code" type="text" inputMode="numeric" autoComplete="one-time-code" required value={code} onChange={(e) => setCode(e.target.value)} style={{ maxWidth: 200 }} />
          <div className="actions">
            <button className="btn btn-primary" type="submit" disabled={code.replace(/\s/g, '').length < 6}>Turn on</button>
            <button className="btn btn-tertiary" type="button" onClick={() => { void supabase.auth.mfa.unenroll({ factorId: enrol.factorId }); setEnrol(null); }}>Cancel</button>
          </div>
        </form>
      )}
      <ConfirmDialog open={!!confirmOff} title="Turn off two-step verification?" confirmLabel="Turn off" destructive onCancel={() => setConfirmOff(null)} onConfirm={() => confirmOff && void turnOff(confirmOff)}>
        <p>Your account will be protected by your password alone.</p>
      </ConfirmDialog>
    </section>
  );
}

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
      <TwoStep />
      <section className="card" aria-labelledby="mine-h">
        <h2 id="mine-h" style={{ marginTop: 0 }}>Your achievements</h2>
        <p><Link to="/certificates">Certificates</Link> · <Link to="/portfolio">Portfolio</Link> · <Link to="/progress">Progress</Link></p>
      </section>
    </main>
  );
}
