import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { Badge } from '../components/Badge';
import { EmptyState, ErrorMessage, Loading } from '../components/States';
import { STATUS_HELP, STATUS_LABEL } from '../components/SubmissionStatus';
import { errorMessage } from '../services/api';
import { getExercise, listSubmissions } from '../services/lectureApi';

/** S15 — chronological official attempts, newest first, with the best valid score kept separate. */
export function AttemptHistory() {
  const { exerciseId = '' } = useParams();
  const exercise = useQuery({ queryKey: ['exercise', exerciseId], queryFn: () => getExercise(exerciseId) });
  const attempts = useQuery({ queryKey: ['submissions', exerciseId], queryFn: () => listSubmissions(exerciseId) });
  if (attempts.isPending || (exercise.isPending && !exercise.isError)) return <main className="page"><Loading label="Loading your attempts…" /></main>;
  // The title is a convenience: attempts stay visible even if the exercise itself is still locked for this learner.
  if (attempts.error || !attempts.data) {
    return <main className="page"><ErrorMessage message={errorMessage(attempts.error)} onRetry={() => { void attempts.refetch(); }} /></main>;
  }
  const list = [...attempts.data.submissions].sort((a, b) => b.submission_number - a.submission_number);
  return (
    <main className="page">
      <p><Link to="/progress">← My progress</Link></p>
      <h1>Attempts: {exercise.data?.title ?? 'this exercise'}</h1>
      <p>
        Best score: <strong>{attempts.data.best_score == null ? 'none yet' : `${attempts.data.best_score}%`}</strong>
        <span className="muted"> — only your best valid score counts, and a new attempt never lowers it.</span>
      </p>
      {list.length === 0 ? <EmptyState title="No official attempts yet">Open the lab and choose Submit for grading when you are ready.</EmptyState> : (
        <div className="table-wrap">
          <table>
            <caption>Official attempts, newest first</caption>
            <thead><tr><th scope="col">Attempt</th><th scope="col">Submitted</th><th scope="col">Result</th><th scope="col">Score</th><th scope="col">Tests</th><th scope="col">Exercise version</th></tr></thead>
            <tbody>
              {list.map((s) => {
                const [kind, label] = STATUS_LABEL[s.status];
                return (
                  <tr key={s.submission_id}>
                    <th scope="row">#{s.submission_number}</th>
                    <td>{new Date(s.created_at).toLocaleString()}</td>
                    <td><Badge kind={kind}>{label}</Badge>{STATUS_HELP[s.status] && s.infrastructure_error && <div className="muted">Not marked incorrect.</div>}</td>
                    <td>{s.score == null ? '—' : `${s.score}%`}</td>
                    <td>{s.total_tests ? `${s.passed_tests} of ${s.total_tests}` : '—'}</td>
                    <td>{s.content_version != null ? `Lesson v${s.content_version}` : '—'}{s.test_suite_version != null ? `, checks v${s.test_suite_version}` : ''}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
