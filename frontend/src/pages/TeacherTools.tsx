import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthProvider';
import { EmptyState, ErrorMessage, Loading } from '../components/States';
import { downloadFile, errorMessage } from '../services/api';
import { archiveAnnouncement, createAnnouncement, getProgressReport, getTeacherCohorts, listMyAnnouncements, progressReportCsvPath } from '../services/adminApi';
import { getCourses } from '../services/lectureApi';

export function CohortsPanel() {
  const q = useQuery({ queryKey: ['t-cohorts'], queryFn: getTeacherCohorts });
  return (
    <section aria-labelledby="coh-h">
      <h2 id="coh-h" style={{ marginTop: 32 }}>Your cohorts</h2>
      {q.isPending && <Loading label="Loading cohorts…" />}
      {q.isError && <ErrorMessage message={errorMessage(q.error)} onRetry={() => void q.refetch()} />}
      {q.data?.length === 0 && <EmptyState title="You are not part of a cohort yet">An administrator groups learners into cohorts and adds you as their teacher. Learners assigned to you individually are listed below.</EmptyState>}
      <div className="grid grid-3">
        {q.data?.map((c) => (
          <div key={c.id} className="tile" role="group" aria-label={`Cohort ${c.name}`}>
            <strong>{c.learners}</strong><span className="tile-label">{c.name}</span>
            <span className="tile-hint">{c.in_progress} in progress · {c.lectures_completed} lectures completed · {c.needs_support} need support</span>
            <Link to={`/teacher/report?cohort=${c.id}`}>Report for this cohort</Link>
          </div>
        ))}
      </div>
    </section>
  );
}

export function ReportExport() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  return (
    <section aria-labelledby="rep-h">
      <h2 id="rep-h" style={{ marginTop: 32 }}>Progress report</h2>
      <p className="muted">One row per learner you can see: lectures, labs passed, attempts, average best score and whether they need support. It contains names and progress only.</p>
      <div className="actions">
        <button className="btn btn-secondary" disabled={busy} onClick={() => { setBusy(true); setError(''); downloadFile(progressReportCsvPath(), 'progress-report.csv').catch((e) => setError(errorMessage(e))).finally(() => setBusy(false)); }}>{busy ? 'Preparing…' : 'Download CSV'}</button>
        <Link className="btn btn-secondary" to="/teacher/report">Open printable report (PDF)</Link>
      </div>
      {error && <p role="alert" className="field-error">{error}</p>}
    </section>
  );
}

export function AnnouncementsPanel() {
  const { role } = useAuth();
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ['t-announcements'], queryFn: listMyAnnouncements });
  const courses = useQuery({ queryKey: ['courses'], queryFn: getCourses });
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [scope, setScope] = useState<'assigned' | 'course'>('assigned');
  const [notice, setNotice] = useState('');
  const send = useMutation({
    mutationFn: () => createAnnouncement(courses.data?.[0]?.id ?? '', title.trim(), body.trim(), scope),
    onSuccess: () => { setNotice('Announcement sent. Learners see it on their dashboard.'); setTitle(''); setBody(''); void qc.invalidateQueries({ queryKey: ['t-announcements'] }); },
    onError: (e) => setNotice(errorMessage(e)),
  });
  const remove = useMutation({ mutationFn: (id: string) => archiveAnnouncement(id), onSuccess: () => { setNotice('Announcement removed.'); void qc.invalidateQueries({ queryKey: ['t-announcements'] }); } });
  return (
    <section aria-labelledby="ann-h">
      <h2 id="ann-h" style={{ marginTop: 32 }}>Announcements</h2>
      {notice && <div role="status" className="notice notice-info"><p>{notice}</p></div>}
      <form className="card" onSubmit={(e) => { e.preventDefault(); setNotice(''); send.mutate(); }} aria-label="Write an announcement">
        <label htmlFor="an-title">Title</label>
        <input id="an-title" type="text" required maxLength={120} value={title} onChange={(e) => setTitle(e.target.value)} />
        <label htmlFor="an-body">Message</label>
        <textarea id="an-body" required maxLength={2000} rows={4} value={body} onChange={(e) => setBody(e.target.value)} />
        {role === 'admin' && (
          <><label htmlFor="an-scope">Who sees it</label>
            <select id="an-scope" value={scope} onChange={(e) => setScope(e.target.value as 'assigned' | 'course')}><option value="assigned">Learners assigned to me</option><option value="course">Everyone enrolled in the course</option></select></>
        )}
        {role !== 'admin' && <p className="field-hint">It goes to the learners assigned to you, not to anyone else.</p>}
        <button className="btn btn-primary" type="submit" disabled={send.isPending || !courses.data?.length}>{send.isPending ? 'Sending…' : 'Send announcement'}</button>
      </form>
      {list.data && list.data.length > 0 && (
        <ul className="plain-list">
          {list.data.map((a) => (
            <li key={a.id} className="card"><strong>{a.title}</strong> <span className="muted">· {a.scope === 'course' ? 'whole course' : 'your learners'} · {new Date(a.created_at).toLocaleString()}</span>
              <p style={{ whiteSpace: 'pre-wrap' }}>{a.body}</p>
              <button className="btn btn-tertiary" onClick={() => remove.mutate(a.id)}>Remove<span className="visually-hidden"> announcement {a.title}</span></button></li>
          ))}
        </ul>
      )}
    </section>
  );
}

/** Printable page: use the browser's "Save as PDF" in the print dialog. */
export function TeacherReport() {
  const cohort = new URLSearchParams(window.location.search).get('cohort') ?? undefined;
  const q = useQuery({ queryKey: ['t-report', cohort], queryFn: () => getProgressReport(cohort) });
  return (
    <main className="page">
      <h1>Progress report</h1>
      <p className="muted">Generated {new Date().toLocaleString()}. Names and progress only.</p>
      <div className="actions no-print"><button className="btn btn-primary" onClick={() => window.print()}>Print or save as PDF</button><Link className="btn btn-secondary" to="/teacher">Back to dashboard</Link></div>
      {q.isPending && <Loading label="Preparing the report…" />}
      {q.isError && <ErrorMessage message={errorMessage(q.error)} onRetry={() => void q.refetch()} />}
      {q.data && (
        <div className="table-wrap">
          <table>
            <caption>{q.data.length} learner{q.data.length === 1 ? '' : 's'}</caption>
            <thead><tr><th scope="col">Learner</th><th scope="col">Lectures completed</th><th scope="col">In progress</th><th scope="col">Labs passed</th><th scope="col">Attempts</th><th scope="col">Average best score</th><th scope="col">Needs support</th><th scope="col">Last active</th></tr></thead>
            <tbody>{q.data.map((r) => <tr key={r.learner}><th scope="row">{r.learner}</th><td>{r.lectures_completed}</td><td>{r.lectures_in_progress}</td><td>{r.exercises_passed}</td><td>{r.attempts}</td><td>{r.average_best_score ?? '—'}</td><td>{r.needs_support ? 'Yes' : 'No'}</td><td>{r.last_active ? new Date(r.last_active).toLocaleDateString() : '—'}</td></tr>)}</tbody>
          </table>
        </div>
      )}
    </main>
  );
}
