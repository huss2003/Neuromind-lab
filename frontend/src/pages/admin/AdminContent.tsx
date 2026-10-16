import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Badge } from '../../components/Badge';
import { ErrorMessage, Loading } from '../../components/States';
import { errorMessage } from '../../services/api';
import { getAdminCourses, getExerciseTests, setLectureStatus, type ExerciseTests } from '../../services/adminApi';
import { PackImport } from './PackImport';

/** Every check of a lab, hidden ones included: the administrator can always see the test definitions. */
function TestsToggle({ exerciseId, title }: { exerciseId: string; title: string }) {
  const [open, setOpen] = useState(false);
  const q = useQuery({ queryKey: ['a-tests', exerciseId], queryFn: () => getExerciseTests(exerciseId), enabled: open });
  return (
    <>
      <button className="btn btn-tertiary" aria-expanded={open} onClick={() => setOpen((v) => !v)}>{open ? 'Hide checks' : 'Show checks'}</button>
      {open && (
        <div aria-label={`Checks for ${title}`} role="region" style={{ marginTop: 6 }}>
          {q.isPending && <Loading label="Loading checks…" />}
          {q.isError && <ErrorMessage message={errorMessage(q.error)} />}
          {q.data && <TestList t={q.data} />}
        </div>
      )}
    </>
  );
}

function TestList({ t }: { t: ExerciseTests }) {
  return (
    <div>
      {t.packages.length > 0 && <p className="muted" style={{ margin: 0 }}>Libraries: {t.packages.join(', ')}</p>}
      {t.tests.length > 0 && (
        <ol>{t.tests.map((x) => (
          <li key={x.test_order}><strong>{x.label ?? `Check ${x.test_order}`}</strong> {x.hidden && <Badge kind="neutral">hidden</Badge>}<br />
            <code style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(x.definition)}</code>{x.remediation && <><br /><span className="muted">Fix: {x.remediation}</span></>}</li>
        ))}</ol>
      )}
      {t.questions.length > 0 && (
        <ol>{t.questions.map((qq) => (
          <li key={qq.question_order}>{qq.prompt} — <strong>answer {qq.correct_option_id}</strong>: {qq.options.find((o) => o.id === qq.correct_option_id)?.text}</li>
        ))}</ol>
      )}
      {t.hints.length > 0 && <p className="muted" style={{ margin: 0 }}>Hints ({t.hints_max} allowed): {t.hints.join(' · ')}</p>}
    </div>
  );
}

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
                    <td>{l.exercises.length === 0 ? '—' : l.exercises.map((e) => <div key={e.id}>{e.title} <span className="muted">({e.lab_kind}{e.scoring === 'pass_fail' ? ', pass/fail' : `, pass mark ${e.pass_threshold ?? '—'}%`}, suite v{e.test_suite_version ?? '—'})</span> <TestsToggle exerciseId={e.id} title={e.title} /></div>)}</td>
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
