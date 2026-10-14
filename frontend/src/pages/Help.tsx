import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { errorMessage } from '../services/api';
import { reportIssue } from '../services/adminApi';

const FAQ: [string, string][] = [
  ['Is my work saved?', 'Your code is saved to your account a moment after you stop typing. The editor shows “All changes saved” only once the server has confirmed it. If you see “Not saved yet”, keep the page open or copy your code.'],
  ['What is the difference between Run and Submit for grading?', 'Run practice runs in your browser, is private and does not count. Submit for grading creates an official attempt that is checked by the grader and can update your best score.'],
  ['How many attempts do I get?', 'You can practise as often as you like. Only your best valid score counts, and a new attempt never lowers it. Platform problems are never counted against you.'],
  ['What does “System error — not your fault” mean?', 'The grader could not finish because of a platform problem. The attempt was not marked incorrect and your best score is unchanged. Submit again.'],
  ['How is lecture completion decided?', 'The server decides. A lecture is complete when you have finished every required section, passed the checkpoints and the exit check, and reached the pass mark on the lab. Playing a video alone never completes a lecture.'],
  ['Why is a lecture locked?', 'Some lectures need an earlier lecture to be completed first. The course map names the prerequisite.'],
];

function ReportForm() {
  const here = useLocation();
  const [category, setCategory] = useState('content');
  const [message, setMessage] = useState('');
  const [page, setPage] = useState((here.state as { from?: string } | null)?.from ?? '');
  const send = useMutation({ mutationFn: () => reportIssue(category, message.trim(), page.trim() || undefined), onSuccess: () => setMessage('') });
  return (
    <section className="card" aria-labelledby="report-h">
      <h2 id="report-h">Report a problem</h2>
      <div className="notice notice-warning">
        <strong>Never share passwords, keys or other secrets</strong> in a message, a screenshot or your code.
      </div>
      {send.isSuccess ? (
        <div role="status" className="notice notice-success">
          <strong>Thank you. Your report was sent.</strong>
          <p>Reference {send.data.reference}. An administrator will look at it. Quote the reference if you ask about it.</p>
          <button className="btn btn-secondary" onClick={() => send.reset()}>Send another report</button>
        </div>
      ) : (
        <form onSubmit={(e) => { e.preventDefault(); send.mutate(); }} aria-label="Report a problem">
          <label htmlFor="rp-cat">What is it about?</label>
          <select id="rp-cat" value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="content">A mistake in a lesson or question</option><option value="grading">A grading result that looks wrong</option>
            <option value="accessibility">Something I cannot use (accessibility)</option><option value="account">My account or signing in</option><option value="other">Something else</option>
          </select>
          <label htmlFor="rp-msg">What happened?</label>
          <textarea id="rp-msg" required minLength={5} maxLength={2000} rows={5} value={message} onChange={(e) => setMessage(e.target.value)} aria-describedby="rp-hint" />
          <p id="rp-hint" className="field-hint">Say what you expected and what you saw. For grading, include the attempt number from your attempt history.</p>
          <label htmlFor="rp-page">Which page? (optional)</label>
          <input id="rp-page" type="text" maxLength={300} value={page} onChange={(e) => setPage(e.target.value)} placeholder="/lectures/…" />
          {send.isError && <p role="alert" className="field-error">{errorMessage(send.error)}</p>}
          <button className="btn btn-primary" type="submit" disabled={send.isPending || message.trim().length < 5} style={{ marginTop: 12 }}>{send.isPending ? 'Sending…' : 'Send report'}</button>
        </form>
      )}
    </section>
  );
}

/** S18 / T16 — guidance, FAQ and the problem report form. */
export function Help() {
  return (
    <main className="page narrow">
      <h1>Help</h1>
      <section className="card" aria-labelledby="faq-h">
        <h2 id="faq-h">Common questions</h2>
        {FAQ.map(([q, a]) => (
          <details key={q} className="faq">
            <summary>{q}</summary>
            <p>{a}</p>
          </details>
        ))}
      </section>
      <ReportForm />
      <p><Link to="/welcome">Read the lab walkthrough again</Link> · <Link to="/policies">Policies</Link> · <Link to="/privacy">Privacy notice</Link> · <Link to="/terms">Terms of use</Link></p>
    </main>
  );
}
