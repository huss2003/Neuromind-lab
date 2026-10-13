import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { Badge } from '../components/Badge';
import { ErrorMessage, Loading } from '../components/States';
import { ApiError, errorMessage } from '../services/api';
import { getSubmissionDetail } from '../services/lectureApi';

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
          {s.status === 'passed' ? <Badge kind="success">Passed</Badge> : s.infrastructure_failure ? <Badge kind="danger">Grader problem (not the learner’s fault)</Badge> : <Badge kind="warning">{s.status === 'timeout' ? 'Timed out' : 'Needs retry'}</Badge>}
        </p>
        <p><strong>Official score:</strong> {s.score != null ? `${s.score}% of ${s.max_score}` : '—'} (pass mark {s.pass_threshold ?? '—'}%)
          {s.hints_used > 0 && <><br /><span className="muted">Raw {s.raw_score}% − {s.hint_penalty} points for {s.hints_used} hint(s)</span></>}</p>
        <p className="muted" style={{ marginBottom: 0 }}>Official scores can't be edited. Use feedback to guide the learner.</p>
      </div>
      <h2>Criteria</h2>
      <ul className="criteria">{s.criteria.map((c, i) => <li key={i}><span aria-hidden="true">{c.passed ? '✓' : '✕'}</span><span><span className="visually-hidden">{c.passed ? 'Passed: ' : 'Not passed: '}</span>{c.label}</span></li>)}</ul>
      <h2>Submitted code</h2>
      <pre className="code" tabIndex={0} aria-label="Submitted code">{s.source_code}</pre>
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
