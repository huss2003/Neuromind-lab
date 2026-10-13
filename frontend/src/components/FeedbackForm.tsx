import { useState, type FormEvent } from 'react';
import { errorMessage } from '../services/api';
import { addFeedback } from '../services/lectureApi';

/** Teacher feedback is a note, never a score change. */
export function FeedbackForm({ learnerId, submissionId, onSaved }: { learnerId: string; submissionId?: string; onSaved: () => void }) {
  const [body, setBody] = useState('');
  const [publish, setPublish] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!body.trim() || busy) return;
    setBusy(true); setError(null); setDone(false);
    try {
      await addFeedback(learnerId, body.trim(), publish, submissionId);
      setBody(''); setDone(true); onSaved();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="card" aria-labelledby="fb-form-title">
      <h2 id="fb-form-title">Leave feedback</h2>
      <p className="muted">Feedback helps the learner but never changes an official score.</p>
      <label htmlFor="fb-body">Message</label>
      <textarea id="fb-body" value={body} maxLength={2000} rows={4} onChange={(e) => setBody(e.target.value)} aria-describedby="fb-count" />
      <p id="fb-count" className="field-hint">{body.length}/2000</p>
      <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontWeight: 400 }}>
        <input type="checkbox" checked={publish} onChange={(e) => setPublish(e.target.checked)} style={{ width: 20, height: 20 }} />
        Share with the learner now
      </label>
      {error && <p role="alert" className="field-error">{error}</p>}
      {done && <p role="status" className="notice notice-success">Feedback saved{publish ? ' and shared' : ' as a private note'}.</p>}
      <div className="actions"><button className="btn btn-primary" type="submit" disabled={busy || !body.trim()}>{busy ? 'Saving…' : 'Save feedback'}</button></div>
    </form>
  );
}
