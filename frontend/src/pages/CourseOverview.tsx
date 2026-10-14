import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { LectureStatus, lectureAction } from '../components/LectureStatus';
import { ProgressBar } from '../components/Progress';
import { EmptyState, ErrorMessage, Loading } from '../components/States';
import { ApiError, errorMessage } from '../services/api';
import { getCourse } from '../services/lectureApi';

export function CourseOverview() {
  const { courseId = '' } = useParams();
  const course = useQuery({ queryKey: ['course', courseId], queryFn: () => getCourse(courseId) });
    if (course.isPending) return <main className="page"><Loading label="Loading course…" /></main>;
  if (course.isError) {
    const missing = course.error instanceof ApiError && course.error.status === 404;
    return <main className="page"><ErrorMessage message={missing ? 'This course was not found or is not published.' : errorMessage(course.error)} onRetry={missing ? undefined : () => void course.refetch()} /><Link to="/">Back to dashboard</Link></main>;
  }
  const c = course.data;
  const done = c.lectures.filter((l) => l.state === 'completed').length;
  const modules = c.modules.length > 0 ? c.modules : [{ id: 'all', module_number: 1, title: 'Lectures', description: '', lectures: c.lectures }];

  return (
    <main className="page">
      <nav className="crumbs" aria-label="Breadcrumb"><Link to="/">Dashboard</Link> <span aria-hidden="true">›</span> <span aria-current="page">{c.title}</span></nav>
      <h1>{c.title}</h1>
      <p>{c.description}</p>
      <div className="card"><ProgressBar label="Course progress" done={done} total={c.lectures.length} tone="success" /></div>
      {modules.length === 0 && <EmptyState title="No modules yet" />}
      {modules.map((m) => (
        <details key={m.id} className="card" open>
          <summary><h2 style={{ display: 'inline' }}>Module {m.module_number}: {m.title}</h2></summary>
          {m.description && <p className="muted">{m.description}</p>}
          {m.lectures.length === 0 && <p className="muted">No lectures are published in this module yet.</p>}
          <ul className="lecture-list">
            {m.lectures.map((l) => (
              <li key={l.id} className={`card row state-${l.state}`} style={{ marginBottom: 0 }}>
                <div>
                  <strong>Lecture {l.lecture_number}: {l.title}</strong>
                  <p className="muted" style={{ margin: 0 }}>{l.summary}{l.duration_seconds ? ` · ${Math.round(l.duration_seconds / 60)} min` : ''}</p>
                  {l.state === 'locked' && <p className="muted" style={{ margin: 0 }}>Complete the earlier lecture first to unlock this one.</p>}
                  {l.state === 'needs_attention' && <p className="muted" style={{ margin: 0 }}>An exercise needs another try — your dashboard has guidance.</p>}
                </div>
                <div className="row">
                  <LectureStatus status={l.state} />
                  {l.state === 'locked'
                    ? <button className="btn btn-secondary" disabled aria-disabled="true">Locked</button>
                    : <Link className="btn btn-primary" to={`/lectures/${l.id}`}>{lectureAction(l.state)}</Link>}
                </div>
              </li>
            ))}
          </ul>
        </details>
      ))}
    </main>
  );
}
