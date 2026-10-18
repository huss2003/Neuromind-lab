import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Badge } from '../components/Badge';
import { Icon } from '../components/Icon';
import { EmptyState, ErrorMessage, Loading } from '../components/States';
import { errorMessage } from '../services/api';
import { getLabs, type LabRow } from '../services/lectureApi';

const KIND_LABEL: Record<LabRow['lab_kind'], string> = { code: 'Coding lab', quiz: 'Question set', written: 'Written task', upload: 'Project upload' };
const STATE: Record<LabRow['state'], [Parameters<typeof Badge>[0]['kind'], string]> = {
  locked: ['neutral', 'Locked'], not_started: ['info', 'Not started'], in_progress: ['info', 'In progress'],
  awaiting_review: ['warning', 'Awaiting teacher review'], needs_retry: ['warning', 'Try again'], passed: ['success', 'Passed'],
};
export const labAction = (state: LabRow['state']) => (state === 'passed' ? 'Review lab' : state === 'not_started' ? 'Open lab' : state === 'needs_retry' ? 'Try again' : 'Continue');

/** Practical Labs: course -> month -> each lecture's lab. States come from the server only. */
export function Labs() {
  const q = useQuery({ queryKey: ['labs'], queryFn: getLabs });
  if (q.isPending) return <main className="page"><Loading label="Loading your labs…" /></main>;
  if (q.isError) return <main className="page"><ErrorMessage message={errorMessage(q.error)} onRetry={() => void q.refetch()} /></main>;
  return (
    <main className="page lab-catalogue">
      <h1>Practical labs</h1>
      <p className="muted">Every lecture from Lecture 9 has a hands-on lab. Python and the lab's libraries run in your browser; your result is checked by the server.</p>
      {q.data.courses.length === 0 && <EmptyState title="No labs yet"><p>You are not enrolled in a course with practical labs. Ask your teacher.</p></EmptyState>}
      {q.data.courses.map((c) => (
        <section key={c.id} aria-labelledby={`course-${c.id}`}>
          <h2 id={`course-${c.id}`}>{c.title}</h2>
          <p className="muted">{c.passed} of {c.total} labs passed.</p>
          {c.modules.filter((m) => m.labs.length > 0).map((m) => (
            <details key={m.id} className="card" open={!m.labs.every((l) => l.state === 'passed')}>
              <summary><h3 style={{ display: 'inline' }}>{m.title}</h3> <span className="muted">· {m.labs.filter((l) => l.state === 'passed').length}/{m.labs.length} passed</span></summary>
              <ul className="lecture-list">
                {m.labs.map((l) => {
                  const [kind, label] = STATE[l.state];
                  return (
                    <li key={l.exercise_id} className={`card row state-${l.state}`} style={{ marginBottom: 0 }}>
                      <div>
                        <strong>Lecture {l.lecture_number}: {l.title}</strong>
                        <p className="muted" style={{ margin: 0 }}><span className="lab-kind">{KIND_LABEL[l.lab_kind]}</span>{l.packages.length > 0 ? ` · uses ${l.packages.join(', ')}` : ''}{l.attempts > 0 ? ` · ${l.attempts} attempt${l.attempts > 1 ? 's' : ''}` : ''}</p>
                        {l.state === 'locked' && <p className="muted" style={{ margin: 0 }}>Complete the earlier lecture first to unlock this lab.</p>}
                      </div>
                      <div className="row">
                        <Badge kind={kind}>{label}</Badge>
                        {l.state === 'locked'
                          ? <button className="btn btn-secondary" disabled aria-disabled="true"><Icon name="lock" size={16} /> Locked</button>
                          : <Link className="btn btn-primary" to={`/labs/${l.exercise_id}`}>{labAction(l.state)}</Link>}
                      </div>
                    </li>
                  );
                })}
              </ul>
            </details>
          ))}
        </section>
      ))}
    </main>
  );
}
