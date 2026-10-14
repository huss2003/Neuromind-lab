import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { Badge, type BadgeKind } from '../components/Badge';
import { FeedbackForm } from '../components/FeedbackForm';
import { EmptyState, ErrorMessage, Loading } from '../components/States';
import { ApiError, errorMessage } from '../services/api';
import { getLearnerResults } from '../services/lectureApi';

const SUB_BADGE: Record<string, [BadgeKind, string]> = {
  passed: ['success', 'Passed'], failed: ['warning', 'Needs work'], runtime_error: ['warning', 'Runtime error'], timeout: ['warning', 'Time limit'],
  error: ['danger', 'Grader problem'], expired: ['danger', 'Grader problem (expired)'], cancelled: ['neutral', 'Cancelled'],
  queued: ['info', 'Queued'], running: ['info', 'Running'],
};
const when = (iso: string) => new Date(iso).toLocaleString();

export function TeacherLearner() {
  const { learnerId = '' } = useParams();
  const qc = useQueryClient();
  const res = useQuery({ queryKey: ['t-results', learnerId], queryFn: () => getLearnerResults(learnerId) });

  if (res.isPending) return <main className="page"><Loading label="Loading learner…" /></main>;
  if (res.isError) {
    const missing = res.error instanceof ApiError && res.error.status === 404;
    return <main className="page"><ErrorMessage message={missing ? 'This learner was not found, or is not assigned to you.' : errorMessage(res.error)} onRetry={missing ? undefined : () => void res.refetch()} /><Link to="/teacher">Back to dashboard</Link></main>;
  }
  const r = res.data;
  return (
    <main className="page">
      <nav className="crumbs" aria-label="Breadcrumb"><Link to="/teacher">Teacher dashboard</Link> <span aria-hidden="true">›</span> <span aria-current="page">{r.learner.display_name || 'Learner'}</span></nav>
      <h1>{r.learner.display_name || 'Learner'}</h1>
      <p className="muted">Records shown here are the official, server-stored results.</p>

      <h2>Lectures</h2>
      {r.sessions.length === 0 ? <EmptyState title="No activity yet">This learner hasn't started a lecture.</EmptyState> : (
        <div className="table-wrap"><table>
          <thead><tr><th scope="col">Lecture</th><th scope="col">Status</th><th scope="col">Last active</th><th scope="col">Completed</th></tr></thead>
          <tbody>{r.sessions.map((s) => (
            <tr key={s.lecture_id}><th scope="row">{s.lecture ?? s.lecture_id.slice(-6)}</th>
              <td>{s.status === 'completed' ? <Badge kind="success">Completed</Badge> : s.status === 'in_progress' ? <Badge kind="info">In progress</Badge> : <Badge kind="neutral">Not started</Badge>}</td>
              <td>{when(s.last_seen_at)}</td><td>{s.completed_at ? when(s.completed_at) : '—'}</td></tr>
          ))}</tbody></table></div>
      )}

      <h2>Best lab scores</h2>
      {r.best_scores.length === 0 ? <p className="muted">No graded attempts yet.</p> : (
        <ul>{r.best_scores.map((b) => <li key={b.exercise_id}>{b.exercise ?? 'Exercise'}: {b.best_score != null ? `${b.best_score}%` : 'no valid score yet'}</li>)}</ul>
      )}

      <h2>Code submissions</h2>
      {r.submissions.length === 0 ? <EmptyState title="No submissions yet" /> : (
        <div className="table-wrap"><table>
          <thead><tr><th scope="col">Exercise</th><th scope="col">#</th><th scope="col">Result</th><th scope="col">Score</th><th scope="col">Hints</th><th scope="col">Checks</th><th scope="col">When</th><th scope="col"><span className="visually-hidden">Open</span></th></tr></thead>
          <tbody>{r.submissions.map((s) => {
            const [kind, label] = SUB_BADGE[s.status] ?? ['neutral', s.status];
            return (
              <tr key={s.submission_id}><th scope="row">{s.exercise ?? 'Exercise'}</th><td>{s.number}</td><td><Badge kind={kind}>{label}</Badge></td>
                <td>{s.score != null ? `${s.score}%` : '—'}</td><td>{s.hints_used}</td><td>{s.passed_tests}/{s.total_tests}</td><td>{when(s.created_at)}</td>
                <td><Link to={`/teacher/submissions/${s.submission_id}`}>Evidence</Link></td></tr>
            );
          })}</tbody></table></div>
      )}

      <h2>Knowledge-check attempts</h2>
      {r.checkpoint_attempts.length === 0 ? <p className="muted">No attempts yet.</p> : (
        <div className="table-wrap"><table>
          <thead><tr><th scope="col">Check</th><th scope="col">Result</th><th scope="col">Score</th><th scope="col">When</th></tr></thead>
          <tbody>{r.checkpoint_attempts.map((a, i) => (
            <tr key={i}><th scope="row">{a.checkpoint ?? 'Checkpoint'}</th><td>{a.is_correct ? '✓ Correct' : '✕ Incorrect'}</td><td>{a.score}</td><td>{when(a.submitted_at)}</td></tr>
          ))}</tbody></table></div>
      )}

      <h2>Feedback given</h2>
      {r.feedback.length === 0 ? <p className="muted">No feedback yet.</p> : (
        <ul>{r.feedback.map((f) => <li key={f.id}>{f.body} <span className="muted">— {when(f.created_at)} · {f.published ? 'shared with learner' : 'private note'}</span></li>)}</ul>
      )}
      <FeedbackForm learnerId={r.learner.id} onSaved={() => void qc.invalidateQueries({ queryKey: ['t-results', learnerId] })} />
    </main>
  );
}
