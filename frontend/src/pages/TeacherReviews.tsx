import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { EmptyState, ErrorMessage, Loading } from '../components/States';
import { errorMessage } from '../services/api';
import { getPendingReviews } from '../services/lectureApi';

/** Written and upload labs waiting for a teacher's rubric decision (assigned learners only). */
export function TeacherReviews() {
  const q = useQuery({ queryKey: ['t-reviews'], queryFn: getPendingReviews });
  if (q.isPending) return <main className="page"><Loading label="Loading reviews…" /></main>;
  if (q.isError) return <main className="page"><ErrorMessage message={errorMessage(q.error)} onRetry={() => void q.refetch()} /></main>;
  const when = (iso: string) => new Date(iso).toLocaleString();
  return (
    <main className="page">
      <nav className="crumbs" aria-label="Breadcrumb"><Link to="/teacher">Teacher dashboard</Link> <span aria-hidden="true">›</span> <span aria-current="page">Reviews</span></nav>
      <h1>Reviews</h1>
      <p className="muted">Written tasks and project uploads from your learners. Your decision becomes the official result of the lab.</p>
      {q.data.total === 0 ? <EmptyState title="Nothing waiting for review" /> : (
        <div className="table-wrap"><table>
          <thead><tr><th scope="col">Learner</th><th scope="col">Lab</th><th scope="col">Lecture</th><th scope="col">Attempt</th><th scope="col">Sent</th><th scope="col"><span className="visually-hidden">Open</span></th></tr></thead>
          <tbody>{q.data.pending.map((p) => (
            <tr key={p.submission_id}><th scope="row">{p.learner ?? 'Learner'}</th><td>{p.exercise ?? '—'}</td><td>{p.lecture ?? '—'}</td><td>{p.number}</td><td>{when(p.created_at)}</td>
              <td><Link className="btn btn-secondary" to={`/teacher/submissions/${p.submission_id}`}>Review</Link></td></tr>
          ))}</tbody></table></div>
      )}
    </main>
  );
}
