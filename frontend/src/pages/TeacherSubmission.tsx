import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Badge } from '../components/Badge';
import { ErrorMessage, Loading } from '../components/States';
import { ApiError, errorMessage } from '../services/api';
import { getSubmissionDetail, reviewSubmission, type SubmissionDetail } from '../services/lectureApi';

function ReviewForm({ s }: { s: SubmissionDetail }) {
  const qc = useQueryClient();
  const [passed, setPassed] = useState<boolean | null>(s.review?.passed ?? null);
  const [feedback, setFeedback] = useState(s.review?.feedback ?? '');
  const [scores, setScores] = useState<Record<string, number>>(Object.fromEntries(s.rubric.map((r) => [r.criterion, s.review?.scores.find((x) => x.criterion === r.criterion)?.points ?? 0])));
  const [error, setError] = useState('');
  const m = useMutation({
    mutationFn: () => reviewSubmission(s.submission_id, { passed: passed === true, feedback: feedback.trim(), scores: s.rubric.map((r) => ({ criterion: r.criterion, points: scores[r.criterion] ?? 0 })) }),
    onSuccess: () => { setError(''); void qc.invalidateQueries({ queryKey: ['t-sub', s.submission_id] }); void qc.invalidateQueries({ queryKey: ['t-reviews'] }); },
    onError: (e) => setError(errorMessage(e)),
  });
  return (
    <form className="card" aria-label="Review" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
      <h2 style={{ marginTop: 0 }}>{s.review ? 'Change your decision' : 'Your decision'}</h2>
      {s.review && <p className="muted">Reviewed {s.review.reviewed_at ? new Date(s.review.reviewed_at).toLocaleString() : ''}: {s.review.passed ? 'passed' : 'not passed'}.</p>}
      {s.rubric.length > 0 && (
        <div className="table-wrap"><table className="rubric-table">
          <thead><tr><th scope="col">Criterion</th><th scope="col">What to look for</th><th scope="col">Points</th></tr></thead>
          <tbody>{s.rubric.map((r) => (
            <tr key={r.criterion}><th scope="row">{r.criterion}</th><td>{r.description}</td>
              <td><label htmlFor={`sc-${r.criterion}`} className="visually-hidden">Points for {r.criterion}</label>
                <input id={`sc-${r.criterion}`} type="number" min={0} max={r.max_points} step={1} value={scores[r.criterion] ?? 0} onChange={(e) => setScores({ ...scores, [r.criterion]: Number(e.target.value) })} /> / {r.max_points}</td></tr>
          ))}</tbody></table></div>
      )}
      <fieldset style={{ border: 0, padding: 0 }}>
        <legend>Outcome</legend>
        <label><input type="radio" name="outcome" checked={passed === true} onChange={() => setPassed(true)} required /> Pass</label>{' '}
        <label><input type="radio" name="outcome" checked={passed === false} onChange={() => setPassed(false)} /> Not yet — try again</label>
      </fieldset>
      <label htmlFor="review-feedback">Feedback for the learner</label>
      <textarea id="review-feedback" rows={5} required maxLength={4000} value={feedback} onChange={(e) => setFeedback(e.target.value)} />
      {error && <p role="alert" className="field-error">{error}</p>}
      {m.isSuccess && <p role="status" className="notice notice-success">Decision saved. The learner can see it now.</p>}
      <div className="actions"><button className="btn btn-primary" type="submit" disabled={m.isPending || passed === null}>{m.isPending ? 'Saving…' : 'Save decision'}</button></div>
    </form>
  );
}

export function TeacherSubmission() {
  const { submissionId = '' } = useParams();
  const q = useQuery({ queryKey: ['t-sub', submissionId], queryFn: () => getSubmissionDetail(submissionId) });
  if (q.isPending) return <main className="page"><Loading label="Loading submission…" /></main>;
  if (q.isError) {
    const missing = q.error instanceof ApiError && q.error.status === 404;
    return <main className="page"><ErrorMessage message={missing ? 'This submission was not found, or you are not assigned to this learner.' : errorMessage(q.error)} /><Link to="/teacher">Back to dashboard</Link></main>;
  }
  const s = q.data;
  const ev = s.evidence;
  return (
    <main className="page">
      <nav className="crumbs" aria-label="Breadcrumb"><Link to="/teacher">Teacher dashboard</Link> <span aria-hidden="true">›</span> <span aria-current="page">Submission {s.number}</span></nav>
      <h1>{s.exercise ?? 'Exercise'} — attempt {s.number}</h1>
      <div className="card">
        <p>
          {s.status === 'passed' ? <Badge kind="success">Passed</Badge> : s.infrastructure_failure ? <Badge kind="danger">Grader problem (not the learner’s fault)</Badge> : <Badge kind="warning">{s.status === 'timeout' ? 'Time limit' : s.status === 'runtime_error' ? 'Runtime error' : 'Needs work'}</Badge>}
        </p>
        <p><strong>Official score:</strong> {s.score != null ? `${s.score}% of ${s.max_score}` : '—'} (pass mark {s.pass_threshold ?? '—'}%)
          {s.hints_used > 0 && <><br /><span className="muted">Raw {s.raw_score}% − {s.hint_penalty} points for {s.hints_used} hint(s)</span></>}</p>
        <p className="muted" style={{ marginBottom: 0 }}>Official scores can't be edited. Use feedback to guide the learner.</p>
      </div>
      <h2>Criteria</h2>
      <ul className="criteria">{s.criteria.map((c, i) => <li key={i}><span aria-hidden="true">{c.passed ? '✓' : '✕'}</span><span><span className="visually-hidden">{c.passed ? 'Passed: ' : 'Not passed: '}</span>{c.label}</span></li>)}</ul>
      {s.lab_kind === 'code' ? (
        <><h2>Submitted code</h2><pre className="code" tabIndex={0} aria-label="Submitted code">{s.source_code}</pre></>
      ) : (
        <>
          <h2>{s.lab_kind === 'written' ? 'Written answer' : 'Project submission'}</h2>
          {s.lab_kind === 'upload' && s.answers && (
            <dl className="card" style={{ display: 'grid', gridTemplateColumns: 'max-content 1fr', gap: '4px 16px' }}>
              <dt className="muted">Link</dt><dd>{typeof s.answers.link === 'string' ? <a href={s.answers.link} rel="noreferrer noopener" target="_blank">{s.answers.link}</a> : '—'}</dd>
              <dt className="muted">Checklist</dt><dd>{Array.isArray(s.answers.checklist) ? `${(s.answers.checklist as boolean[]).filter(Boolean).length} of ${s.checklist.length} ticked` : '—'}</dd>
            </dl>
          )}
          <pre className="code" tabIndex={0} aria-label={s.lab_kind === 'written' ? 'Written answer' : 'Notes'} style={{ whiteSpace: 'pre-wrap' }}>{s.source_code || '(no notes)'}</pre>
          <ReviewForm s={s} />
        </>
      )}
      <h2>Evidence record</h2>
      <dl className="card" style={{ display: 'grid', gridTemplateColumns: 'max-content 1fr', gap: '4px 16px' }}>
        <dt className="muted">Submitted</dt><dd>{new Date(s.created_at).toLocaleString()}</dd>
        <dt className="muted">Started / finished</dt><dd>{ev.started_at ? new Date(ev.started_at).toLocaleTimeString() : '—'} / {ev.finished_at ? new Date(ev.finished_at).toLocaleTimeString() : '—'}</dd>
        <dt className="muted">Run time</dt><dd>{s.execution_ms != null ? `${s.execution_ms} ms` : '—'}</dd>
        <dt className="muted">Grader version</dt><dd>{ev.grader_version ?? '—'}</dd>
        <dt className="muted">Test suite version</dt><dd>{ev.test_suite_version ?? '—'}</dd>
        <dt className="muted">Content version</dt><dd>{ev.content_version ?? '—'}</dd>
        <dt className="muted">Correlation ID</dt><dd><code>{ev.correlation_id ?? '—'}</code></dd>
      </dl>
    </main>
  );
}
