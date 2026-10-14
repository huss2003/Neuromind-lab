import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Badge } from '../../components/Badge';
import { EmptyState, ErrorMessage, Loading } from '../../components/States';
import { errorMessage } from '../../services/api';
import { listIssues, updateIssue, type IssueRow } from '../../services/adminApi';

const PAGE = 10;

function IssueCard({ i, onDone }: { i: IssueRow; onDone: (m: string) => void }) {
  const [note, setNote] = useState(i.admin_note ?? '');
  const m = useMutation({ mutationFn: (status: string) => updateIssue(i.id, status, note), onSuccess: (_d, s) => onDone(`Report ${i.reference} marked ${s}.`), onError: (e) => onDone(errorMessage(e)) });
  return (
    <section className="card" aria-labelledby={`is-${i.id}`}>
      <h2 id={`is-${i.id}`} style={{ marginTop: 0 }}>Report {i.reference} <Badge kind={i.status === "open" ? "warning" : "neutral"}>{i.status}</Badge></h2>
      <p className="muted">{i.category} · from {i.reporter} · {new Date(i.created_at).toLocaleString()}{i.page ? ` · page ${i.page}` : ''}</p>
      <p style={{ whiteSpace: 'pre-wrap' }}>{i.message}</p>
      <label htmlFor={`n-${i.id}`}>Note (visible to administrators only)</label>
      <textarea id={`n-${i.id}`} rows={2} maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)} />
      <div className="actions">
        {(['triaged', 'resolved', 'dismissed', 'open'] as const).filter((s) => s !== i.status).map((s) => (
          <button key={s} className="btn btn-secondary" disabled={m.isPending} onClick={() => m.mutate(s)}>Mark {s}<span className="visually-hidden"> report {i.reference}</span></button>
        ))}
      </div>
    </section>
  );
}

export function AdminIssues() {
  const qc = useQueryClient();
  const [status, setStatus] = useState('open');
  const [offset, setOffset] = useState(0);
  const [notice, setNotice] = useState('');
  const q = useQuery({ queryKey: ['a-issues', status, offset], queryFn: () => listIssues(status, PAGE, offset) });
  const total = q.data?.total ?? 0;
  return (
    <section aria-label="Issue reports">
      <p className="muted">Problems reported by learners and teachers: content mistakes, grading questions, accessibility barriers and account trouble.</p>
      {notice && <div role="status" className="notice notice-info"><p>{notice}</p></div>}
      <label htmlFor="is-status">Show</label>
      <select id="is-status" value={status} onChange={(e) => { setOffset(0); setStatus(e.target.value); }} style={{ maxWidth: 220 }}>
        <option value="open">Open</option><option value="triaged">Triaged</option><option value="resolved">Resolved</option><option value="dismissed">Dismissed</option><option value="any">All</option>
      </select>
      {q.isPending && <Loading label="Loading reports…" />}
      {q.isError && <ErrorMessage message={errorMessage(q.error)} onRetry={() => void q.refetch()} />}
      {q.data?.issues.length === 0 && <EmptyState title="No reports here">Nothing matches this filter.</EmptyState>}
      {q.data?.issues.map((i) => <IssueCard key={`${i.id}-${i.status}`} i={i} onDone={(m) => { setNotice(m); void qc.invalidateQueries({ queryKey: ['a-issues'] }); void qc.invalidateQueries({ queryKey: ['a-overview'] }); }} />)}
      {total > PAGE && (
        <nav className="actions" aria-label="Pagination">
          <button className="btn btn-secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>Previous</button>
          <span className="muted" style={{ alignSelf: 'center' }}>Showing {offset + 1}–{Math.min(offset + PAGE, total)} of {total}</span>
          <button className="btn btn-secondary" disabled={offset + PAGE >= total} onClick={() => setOffset(offset + PAGE)}>Next</button>
        </nav>
      )}
    </section>
  );
}
