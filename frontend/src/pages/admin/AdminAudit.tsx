import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { EmptyState, ErrorMessage, Loading } from '../../components/States';
import { errorMessage } from '../../services/api';
import { listAudit } from '../../services/adminApi';

const PAGE = 25;
const KNOWN = ['auth.denied', 'admin.role_changed', 'admin.user_created', 'admin.user_deactivated', 'admin.user_reactivated', 'admin.enrolled', 'admin.teacher_assigned', 'admin.submission_requeued',
  'admin.lecture_status_changed', 'certificate.issued', 'submission.created', 'submission.rate_limited', 'teacher.view_learner', 'teacher.view_submission', 'teacher.report_exported', 'issue.reported', 'lecture.completed'];

export function AdminAudit() {
  const [type, setType] = useState('');
  const [offset, setOffset] = useState(0);
  const q = useQuery({ queryKey: ['a-audit', type, offset], queryFn: () => listAudit({ event_type: type || undefined, limit: PAGE, offset }) });
  const total = q.data?.total ?? 0;
  return (
    <section aria-label="Audit log">
      <p className="muted">Security and administrative events. They record who did what and when, never passwords, tokens, code or answers.</p>
      <div className="actions">
        <label htmlFor="audit-type" className="visually-hidden">Filter by event type</label>
        <select id="audit-type" value={type} onChange={(e) => { setOffset(0); setType(e.target.value); }} style={{ maxWidth: 320 }}>
          <option value="">All events</option>
          {KNOWN.map((k) => <option key={k} value={k}>{k}</option>)}
        </select>
      </div>
      {q.isPending && <Loading label="Loading events…" />}
      {q.isError && <ErrorMessage message={errorMessage(q.error)} onRetry={() => void q.refetch()} />}
      {q.data?.events.length === 0 && <EmptyState title="No events">Nothing matches this filter.</EmptyState>}
      {q.data && q.data.events.length > 0 && (
        <>
          <div className="table-wrap">
            <table>
              <caption>Events ({total})</caption>
              <thead><tr><th scope="col">When</th><th scope="col">Event</th><th scope="col">Actor</th><th scope="col">Resource</th><th scope="col">Details</th></tr></thead>
              <tbody>
                {q.data.events.map((e) => (
                  <tr key={e.id}>
                    <td>{new Date(e.created_at).toLocaleString()}</td><th scope="row">{e.event_type}</th>
                    <td>{e.actor_id ? e.actor_id.slice(0, 8) : 'system'}</td><td>{e.resource_type}{e.resource_id ? ` ${e.resource_id.slice(0, 8)}` : ''}</td>
                    <td>{Object.keys(e.metadata).length ? Object.entries(e.metadata).map(([k, v]) => `${k}: ${String(v)}`).join(', ') : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <nav className="actions" aria-label="Pagination">
            <button className="btn btn-secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>Newer</button>
            <span className="muted" style={{ alignSelf: 'center' }}>Showing {offset + 1}–{Math.min(offset + PAGE, total)} of {total}</span>
            <button className="btn btn-secondary" disabled={offset + PAGE >= total} onClick={() => setOffset(offset + PAGE)}>Older</button>
          </nav>
        </>
      )}
    </section>
  );
}
