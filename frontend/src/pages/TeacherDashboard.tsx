import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { EmptyState, ErrorMessage, Loading } from '../components/States';
import { errorMessage } from '../services/api';
import { getTeacherSummary, listLearners } from '../services/lectureApi';

const PAGE = 10;

export function TeacherDashboard() {
  const [q, setQ] = useState('');
  const [term, setTerm] = useState('');
  const [offset, setOffset] = useState(0);
  const summary = useQuery({ queryKey: ['t-summary'], queryFn: getTeacherSummary });
  const learners = useQuery({ queryKey: ['t-learners', term, offset], queryFn: () => listLearners(term, PAGE, offset) });

  const tiles: [string, number | undefined, string][] = [
    ['Assigned learners', summary.data?.assigned_learners, 'learners you can review'],
    ['Lectures completed', summary.data?.lectures_completed, 'across assigned learners'],
    ['Lectures in progress', summary.data?.lectures_in_progress, 'currently being studied'],
    ['Labs passed', summary.data?.submissions_passed, 'official passing submissions'],
    ['Labs needing retry', summary.data?.submissions_needing_retry, 'failed or timed out'],
    ['Grader problems', summary.data?.infrastructure_failures, 'not the learner’s fault'],
  ];
  const total = learners.data?.total ?? 0;

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
      <form role="search" className="actions" onSubmit={(e) => { e.preventDefault(); setOffset(0); setTerm(q.trim()); }}>
        <label htmlFor="learner-search" className="visually-hidden">Search learners by name</label>
        <input id="learner-search" type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by name" style={{ maxWidth: 320 }} />
        <button className="btn btn-secondary" type="submit">Search</button>
        {term && <button className="btn btn-tertiary" type="button" onClick={() => { setQ(''); setTerm(''); setOffset(0); }}>Clear</button>}
      </form>
      {learners.isPending && <Loading label="Loading learners…" />}
      {learners.isError && <ErrorMessage message={errorMessage(learners.error)} onRetry={() => void learners.refetch()} />}
      {learners.data && learners.data.learners.length === 0 && (
        <EmptyState title={term ? 'No learners match your search' : 'No learners are assigned to you yet'}>
          {term ? 'Try a different name.' : 'When an administrator assigns learners to you, they will appear here.'}
        </EmptyState>
      )}
      {learners.data && learners.data.learners.length > 0 && (
        <>
          <div className="table-wrap">
            <table>
              <caption>Learners ({total})</caption>
              <thead><tr><th scope="col">Name</th><th scope="col"><span className="visually-hidden">Actions</span></th></tr></thead>
              <tbody>
                {learners.data.learners.map((l) => (
                  <tr key={l.id}><th scope="row">{l.display_name || l.id.slice(0, 8)}</th><td><Link to={`/teacher/learners/${l.id}`}>View progress and evidence</Link></td></tr>
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
    </main>
  );
}
