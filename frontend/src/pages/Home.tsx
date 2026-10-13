import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Badge } from '../components/Badge';
import { ProgressRing } from '../components/Progress';
import { EmptyState, ErrorMessage, Loading } from '../components/States';
import { STATUS_LABEL } from '../components/SubmissionStatus';
import { useAuth } from '../auth/AuthProvider';
import { errorMessage } from '../services/api';
import { getDashboard, getMyFeedback } from '../services/lectureApi';
import type { Submission } from '../services/types';

const when = (iso: string) => new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });

export function Home() {
  const { profile, session } = useAuth();
  const dash = useQuery({ queryKey: ['dashboard'], queryFn: getDashboard });
  const feedback = useQuery({ queryKey: ['feedback'], queryFn: getMyFeedback });

  if (dash.isPending) return <main className="page"><Loading label="Loading your dashboard…" /></main>;
  if (dash.isError) return <main className="page"><ErrorMessage message={errorMessage(dash.error)} onRetry={() => void dash.refetch()} /></main>;
  const d = dash.data;
  const name = (profile?.display_name || session?.user.email || '').split('@')[0];

  if (!d.enrolled || !d.course) {
    return (
      <main className="page">
        <h1>Welcome{name ? `, ${name}` : ''}</h1>
        <EmptyState title="You are not enrolled in a course yet">
          Ask your teacher or an administrator to enrol you. Once they do, your course will appear here.
        </EmptyState>
      </main>
    );
  }
  const next = d.continue;
  const resuming = next && (next.state === 'in_progress' || next.state === 'needs_attention');

  return (
    <main className="page">
      <section className="hero" aria-labelledby="hero-title">
        <div>
          <p style={{ opacity: .85 }}>Welcome back{name ? `, ${name}` : ''}</p>
          <h1 id="hero-title">{next ? `${resuming ? 'Continue' : 'Start'}: Lecture ${next.lecture_number}` : 'You are all caught up'}</h1>
          {next && <p>{next.title}</p>}
        </div>
        {next
          ? <Link className="btn btn-primary" to={`/lectures/${next.lecture_id}`}>{resuming ? 'Resume lecture' : 'Start lecture'}</Link>
          : <Link className="btn btn-primary" to={`/courses/${d.course.id}`}>Review course</Link>}
      </section>

      <div className="grid grid-2">
        <section className="card" aria-labelledby="course-title">
          <h2 id="course-title">{d.course.title}</h2>
          <p className="muted">{d.course.description}</p>
          <ProgressRing done={d.course.completed_lectures} total={d.course.total_lectures} label="lectures completed" />
          <div className="actions"><Link className="btn btn-secondary" to={`/courses/${d.course.id}`}>Open course map</Link></div>
        </section>

        <section className="card" aria-labelledby="rem-title">
          <h2 id="rem-title">Next steps to improve</h2>
          {d.remediation_queue.length === 0 ? <p className="muted">Nothing needs fixing right now. If an exercise doesn't pass, targeted guidance appears here.</p> : (
            <ul className="plain">
              {d.remediation_queue.map((r) => (
                <li key={r.exercise_id}>
                  <strong>{r.exercise ?? 'Exercise'}</strong>{r.lecture ? <span className="muted"> · {r.lecture}</span> : null}
                  {r.objectives.length > 0 && <p style={{ margin: '2px 0' }}>Focus on: {r.objectives.join(', ')}</p>}
                  {r.steps.slice(0, 2).map((s, i) => <p key={i} className="muted" style={{ margin: '2px 0' }}>{s.text}</p>)}
                  {r.lecture_id && <Link to={`/lectures/${r.lecture_id}`}>Go back to the exercise</Link>}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="card" aria-labelledby="att-title">
          <h2 id="att-title">Recent attempts</h2>
          {d.recent_attempts.length === 0 ? <p className="muted">You haven't submitted any code yet. Official attempts you make in a lab will be listed here.</p> : (
            <div className="table-wrap">
              <table>
                <thead><tr><th scope="col">Exercise</th><th scope="col">Result</th><th scope="col">Score</th><th scope="col">Best</th><th scope="col">When</th></tr></thead>
                <tbody>
                  {d.recent_attempts.map((a) => {
                    const st = STATUS_LABEL[a.status as Submission['status']];
                    return (
                      <tr key={a.submission_id}>
                        <th scope="row">{a.exercise ?? 'Exercise'} <span className="muted">#{a.number}</span></th>
                        <td>{st ? <Badge kind={st[0]}>{st[1]}</Badge> : a.status}</td>
                        <td>{a.score != null ? `${a.score}%` : '—'}</td><td>{a.best_score != null ? `${a.best_score}%` : '—'}</td><td>{when(a.created_at)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="card" aria-labelledby="fb-title">
          <h2 id="fb-title">Notes from your teacher</h2>
          {feedback.isPending && <Loading />}
          {feedback.isError && <p className="muted">Notes couldn't be loaded right now.</p>}
          {feedback.data?.length === 0 && <p className="muted">No notes yet. When your teacher shares feedback, it will appear here.</p>}
          <ul className="plain">{feedback.data?.slice(0, 3).map((f) => <li key={f.id}>{f.body}<span className="muted"> — {when(f.created_at)}</span></li>)}</ul>
        </section>
      </div>
    </main>
  );
}
