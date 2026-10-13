import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Badge } from '../components/Badge';
import { EmptyState, ErrorMessage, Loading } from '../components/States';
import { errorMessage } from '../services/api';
import { getContentStatus, getExerciseAnalytics, getTeacherSummary, listLearners } from '../services/lectureApi';

const PAGE = 10;
const when = (iso?: string | null) => (iso ? new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : '—');

export function TeacherDashboard() {
  const [q, setQ] = useState('');
  const [term, setTerm] = useState('');
  const [offset, setOffset] = useState(0);
  const [needsSupport, setNeedsSupport] = useState(false);
  const [progress, setProgress] = useState('any');
  const summary = useQuery({ queryKey: ['t-summary'], queryFn: getTeacherSummary });
  const learners = useQuery({ queryKey: ['t-learners', term, offset, needsSupport, progress], queryFn: () => listLearners(term, PAGE, offset, { needsSupport, progress }) });
  const analytics = useQuery({ queryKey: ['t-analytics'], queryFn: getExerciseAnalytics });
  const content = useQuery({ queryKey: ['t-content'], queryFn: getContentStatus });

  const tiles: [string, number | undefined, string][] = [
    ['Assigned learners', summary.data?.assigned_learners, 'learners you can review'],
    ['Lectures completed', summary.data?.lectures_completed, 'across assigned learners'],
    ['Lectures in progress', summary.data?.lectures_in_progress, 'currently being studied'],
    ['Labs passed', summary.data?.submissions_passed, 'official passing submissions'],
    ['Labs needing work', summary.data?.submissions_needing_retry, 'evaluated, not yet passed'],
    ['Grader problems', summary.data?.infrastructure_failures, 'not the learner’s fault'],
  ];
  const total = learners.data?.total ?? 0;
  const reset = () => setOffset(0);

  return (
    <main className="page">
      <h1>Teacher dashboard</h1>
      {summary.isError && <ErrorMessage message={errorMessage(summary.error)} onRetry={() => void summary.refetch()} />}
      <div className="grid grid-4" aria-busy={summary.isPending}>
        {tiles.map(([label, value, hint]) => (
          <div key={label} className="tile"><strong>{value ?? '—'}</strong><span className="tile-label">{label}</span><span className="tile-hint">{hint}</span></div>
        ))}
      </div>

      <h2 style={{ marginTop: 32 }}>Learners</h2>
      <form role="search" className="actions" onSubmit={(e) => { e.preventDefault(); reset(); setTerm(q.trim()); }}>
        <label htmlFor="learner-search" className="visually-hidden">Search learners by name</label>
        <input id="learner-search" type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by name" style={{ maxWidth: 260 }} />
        <label htmlFor="progress-filter" className="visually-hidden">Progress</label>
        <select id="progress-filter" value={progress} onChange={(e) => { reset(); setProgress(e.target.value); }} style={{ maxWidth: 200 }}>
          <option value="any">Any progress</option><option value="not_started">Not started</option><option value="in_progress">In progress</option><option value="completed">Has completed a lecture</option>
        </select>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 400, margin: 0 }}>
          <input type="checkbox" checked={needsSupport} onChange={(e) => { reset(); setNeedsSupport(e.target.checked); }} style={{ width: 20, height: 20 }} /> Needs support
        </label>
        <button className="btn btn-secondary" type="submit">Search</button>
        {(term || needsSupport || progress !== 'any') && <button className="btn btn-tertiary" type="button" onClick={() => { setQ(''); setTerm(''); setNeedsSupport(false); setProgress('any'); reset(); }}>Clear filters</button>}
      </form>
      {learners.isPending && <Loading label="Loading learners…" />}
      {learners.isError && <ErrorMessage message={errorMessage(learners.error)} onRetry={() => void learners.refetch()} />}
      {learners.data && learners.data.learners.length === 0 && (
        <EmptyState title={term || needsSupport || progress !== 'any' ? 'No learners match these filters' : 'No learners are assigned to you yet'}>
          {term || needsSupport || progress !== 'any' ? 'Try clearing a filter.' : 'When an administrator assigns learners to you, they will appear here.'}
        </EmptyState>
      )}
      {learners.data && learners.data.learners.length > 0 && (
        <>
          <div className="table-wrap">
            <table>
              <caption>Learners ({total})</caption>
              <thead><tr><th scope="col">Name</th><th scope="col">Completed</th><th scope="col">In progress</th><th scope="col">Status</th><th scope="col">Last active</th><th scope="col"><span className="visually-hidden">Actions</span></th></tr></thead>
              <tbody>
                {learners.data.learners.map((l) => (
                  <tr key={l.id}>
                    <th scope="row">{l.display_name || l.id.slice(0, 8)}</th>
                    <td>{l.lectures_completed}</td><td>{l.lectures_in_progress}</td>
                    <td>{l.needs_support ? <Badge kind="warning">Needs support</Badge> : <Badge kind="neutral">On track</Badge>}{l.grader_problems > 0 && <> <Badge kind="danger">{`${l.grader_problems} grader problem${l.grader_problems > 1 ? 's' : ''}`}</Badge></>}</td>
                    <td>{when(l.last_active)}</td>
                    <td><Link to={`/teacher/learners/${l.id}`}>View progress and evidence</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <nav className="actions" aria-label="Pagination">
            <button className="btn btn-secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>Previous</button>
            <span className="muted" style={{ alignSelf: 'center' }}>Showing {offset + 1}–{Math.min(offset + PAGE, total)} of {total}</span>
            <button className="btn btn-secondary" disabled={offset + PAGE >= total} onClick={() => setOffset(offset + PAGE)}>Next</button>
          </nav>
        </>
      )}

      <h2 style={{ marginTop: 32 }}>Exercise analytics</h2>
      {analytics.isPending && <Loading />}
      {analytics.isError && <ErrorMessage message={errorMessage(analytics.error)} />}
      {analytics.data?.length === 0 && <EmptyState title="No submissions yet">Analytics appear after your learners submit code.</EmptyState>}
      {analytics.data?.map((a) => (
        <section key={a.exercise_id} className="card" aria-label={`Analytics for ${a.exercise ?? 'exercise'}`}>
          <h3 style={{ marginTop: 0 }}>{a.exercise ?? 'Exercise'}</h3>
          <p>{a.attempts} attempts by {a.learners} learner{a.learners !== 1 ? 's' : ''} · completion {a.completion_rate}% · average score {a.average_score ?? '—'}% · grader problems {a.system_errors}</p>
          <p className="muted">Scores: below 50% — {a.score_distribution.below_50} · 50–79% — {a.score_distribution['50_to_79']} · 80%+ — {a.score_distribution['80_and_above']}</p>
          {a.common_failures.length > 0 && <><strong>Most common failing criteria</strong><ul>{a.common_failures.map((f) => <li key={f.criterion}>{f.criterion} — {f.count} time{f.count !== 1 ? 's' : ''}</li>)}</ul></>}
        </section>
      ))}

      <h2 style={{ marginTop: 32 }}>Content status</h2>
      {content.isPending && <Loading />}
      {content.data && (
        <div className="table-wrap"><table>
          <thead><tr><th scope="col">Lecture</th><th scope="col">Status</th><th scope="col">Version in use</th></tr></thead>
          <tbody>{content.data.map((c) => <tr key={c.id}><th scope="row">Lecture {c.lecture_number}: {c.title}</th><td>{c.status}</td><td>v{c.version}</td></tr>)}</tbody>
        </table></div>
      )}
      <p className="muted">Editing, review and publishing of content isn't enabled in this version.</p>
    </main>
  );
}
