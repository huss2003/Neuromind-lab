import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Badge } from '../../components/Badge';
import { ErrorMessage, Loading } from '../../components/States';
import { errorMessage } from '../../services/api';
import { getAdminCourses, setLectureStatus } from '../../services/adminApi';
import { PackImport } from './PackImport';

export function AdminContent() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ['a-courses'], queryFn: getAdminCourses });
  const [notice, setNotice] = useState('');
  const change = useMutation({
    mutationFn: (v: { id: string; status: string; title: string }) => setLectureStatus(v.id, v.status),
    onSuccess: (_d, v) => { setNotice(`${v.title} is now ${v.status}.`); void qc.invalidateQueries({ queryKey: ['a-courses'] }); },
    onError: (e) => setNotice(errorMessage(e)),
  });
  if (q.isPending) return <Loading label="Loading content…" />;
  if (q.isError) return <ErrorMessage message={errorMessage(q.error)} onRetry={() => void q.refetch()} />;
  return (
    <section aria-label="Content">
      <p className="muted">{q.data.note} Lectures are added by importing a lecture pack below; hidden test definitions are never shown.</p>
      <PackImport />
      {notice && <div role="status" className="notice notice-info"><p>{notice}</p></div>}
      {q.data.courses.map((c) => (
        <section key={c.id} className="card" aria-labelledby={`c-${c.id}`}>
          <h2 id={`c-${c.id}`} style={{ marginTop: 0 }}>{c.title} <Badge kind={c.status === 'published' ? 'success' : 'neutral'}>{c.status}</Badge></h2>
          <p>{c.learners_enrolled} learner{c.learners_enrolled === 1 ? '' : 's'} enrolled.</p>
          <div className="table-wrap">
            <table>
              <thead><tr><th scope="col">Lecture</th><th scope="col">Status</th><th scope="col">Version</th><th scope="col">Labs (test suite version, pass mark)</th><th scope="col">Change status</th></tr></thead>
              <tbody>
                {c.lectures.map((l) => (
                  <tr key={l.id}>
                    <th scope="row">Lecture {l.lecture_number}: {l.title}</th>
                    <td>{l.status}</td><td>{l.content_version ? `v${l.content_version}` : '—'}</td>
                    <td>{l.exercises.length === 0 ? '—' : l.exercises.map((e) => <div key={e.id}>{e.title} (suite v{e.test_suite_version ?? '—'}, {e.pass_threshold ?? '—'}%)</div>)}</td>
                    <td>
                      <label htmlFor={`st-${l.id}`} className="visually-hidden">Status of lecture {l.lecture_number}</label>
                      <select id={`st-${l.id}`} value={l.status} onChange={(e) => change.mutate({ id: l.id, status: e.target.value, title: `Lecture ${l.lecture_number}` })} disabled={change.isPending} style={{ minHeight: 38, padding: '4px 8px' }}>
                        <option value="draft">Draft</option><option value="published">Published</option><option value="archived">Archived</option>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}
    </section>
  );
}
