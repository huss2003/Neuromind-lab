import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { ErrorMessage, Loading } from '../components/States';
import { errorMessage } from '../services/api';
import { getLearnerResults, listLearners } from '../services/lectureApi';

export function TeacherResults() {
  const [selected, setSelected] = useState<string | null>(null);
  const learners = useQuery({ queryKey: ['learners'], queryFn: listLearners });
  const results = useQuery({ queryKey: ['results', selected], queryFn: () => getLearnerResults(selected!), enabled: !!selected });

  return (
    <main>
      <h1>Learner results</h1>
      {learners.isPending && <Loading />}
      {learners.isError && <ErrorMessage message={errorMessage(learners.error)} />}
      {learners.data?.length === 0 && <p>No learners have signed up yet.</p>}
      {learners.data && learners.data.length > 0 && (
        <>
          <label htmlFor="learner">Learner</label>{' '}
          <select id="learner" value={selected ?? ''} onChange={(e) => setSelected(e.target.value || null)}>
            <option value="">Choose a learner…</option>
            {learners.data.map((l) => <option key={l.id} value={l.id}>{l.display_name || l.id.slice(0, 8)}</option>)}
          </select>
        </>
      )}
      {selected && results.isPending && <Loading label="Loading results…" />}
      {results.isError && <ErrorMessage message={errorMessage(results.error)} />}
      {results.data && (
        <section aria-live="polite">
          <h2>Lectures</h2>
          <table>
            <thead><tr><th>Lecture</th><th>Status</th><th>Last active</th></tr></thead>
            <tbody>{results.data.sessions.map((s) => <tr key={s.lecture_id}><td>{s.lecture_id.slice(-4)}</td><td>{s.status}</td><td>{new Date(s.last_seen_at).toLocaleString()}</td></tr>)}</tbody>
          </table>
          <h2>Checkpoint attempts</h2>
          <table>
            <thead><tr><th>Checkpoint</th><th>Result</th><th>Score</th><th>When</th></tr></thead>
            <tbody>{results.data.checkpoint_attempts.map((a, i) => <tr key={i}><td>{a.checkpoint_id.slice(-4)}</td><td>{a.is_correct ? '✓ Correct' : '✕ Incorrect'}</td><td>{a.score}</td><td>{new Date(a.submitted_at).toLocaleString()}</td></tr>)}</tbody>
          </table>
          <h2>Code submissions</h2>
          <table>
            <thead><tr><th>#</th><th>Status</th><th>Score</th><th>Tests</th><th>When</th></tr></thead>
            <tbody>{results.data.submissions.map((s) => <tr key={s.submission_id}><td>{s.number}</td><td>{s.status}</td><td>{s.score ?? '—'}</td><td>{s.passed_tests}/{s.total_tests}</td><td>{new Date(s.created_at).toLocaleString()}</td></tr>)}</tbody>
          </table>
        </section>
      )}
    </main>
  );
}
