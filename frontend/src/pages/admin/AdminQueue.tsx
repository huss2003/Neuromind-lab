import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { EmptyState, ErrorMessage, Loading } from '../../components/States';
import { errorMessage } from '../../services/api';
import { getAdminQueue, requeueSubmission } from '../../services/adminApi';

const secs = (v: number | null | undefined) => (v === null || v === undefined ? '—' : `${v.toFixed(1)} s`);

export function AdminQueue() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ['a-queue'], queryFn: getAdminQueue, refetchInterval: 15_000 });
  const [target, setTarget] = useState<string | null>(null);
  const [notice, setNotice] = useState('');
  const requeue = useMutation({
    mutationFn: (id: string) => requeueSubmission(id),
    onSuccess: () => { setNotice('The attempt is back in the queue. A worker will pick it up shortly.'); setTarget(null); void qc.invalidateQueries({ queryKey: ['a-queue'] }); },
    onError: (e) => { setNotice(errorMessage(e)); setTarget(null); },
  });
  if (q.isPending) return <Loading label="Loading the grading queue…" />;
  if (q.isError) return <ErrorMessage message={errorMessage(q.error)} onRetry={() => void q.refetch()} />;
  const { queue, grading_24h: g, dead_letters: dead } = q.data;
  return (
    <section aria-label="Grading queue">
      {notice && <div role="status" className="notice notice-info"><p>{notice}</p></div>}
      <div className="grid grid-3">
        <div className="tile"><strong>{queue.queued}</strong><span className="tile-label">Waiting</span><span className="tile-hint">{queue.oldest_queued_seconds === null ? 'nothing waiting' : `oldest ${queue.oldest_queued_seconds} s`}</span></div>
        <div className="tile"><strong>{queue.running}</strong><span className="tile-label">Running</span><span className="tile-hint">held by a worker</span></div>
        <div className="tile"><strong>{dead.length}</strong><span className="tile-label">Could not be graded</span><span className="tile-hint">needs an administrator</span></div>
      </div>
      <h2>Timing, last 24 hours</h2>
      <div className="table-wrap">
        <table>
          <caption>{g.sample} graded attempts measured</caption>
          <thead><tr><th scope="col">Measure</th><th scope="col">Median</th><th scope="col">95th percentile</th><th scope="col">Slowest</th></tr></thead>
          <tbody>
            <tr><th scope="row">Queue wait (submitted until a worker starts)</th><td>{secs(g.queue_wait_seconds.p50)}</td><td>{secs(g.queue_wait_seconds.p95)}</td><td>{secs(g.queue_wait_seconds.max)}</td></tr>
            <tr><th scope="row">Execution (worker starts until the result)</th><td>{secs(g.execution_seconds.p50)}</td><td>{secs(g.execution_seconds.p95)}</td><td>{secs(g.execution_seconds.max)}</td></tr>
            <tr><th scope="row">End to end</th><td>{secs(g.end_to_end_seconds.p50)}</td><td>{secs(g.end_to_end_seconds.p95)}</td><td>{secs(g.end_to_end_seconds.max)}</td></tr>
          </tbody>
        </table>
      </div>
      <h2>Attempts that could not be graded</h2>
      <p className="muted">{q.data.procedure}</p>
      {dead.length === 0 ? <EmptyState title="Nothing stuck">Every attempt has been graded or is still in progress.</EmptyState> : (
        <div className="table-wrap">
          <table>
            <thead><tr><th scope="col">Attempt</th><th scope="col">Submitted</th><th scope="col">Tries</th><th scope="col"><span className="visually-hidden">Actions</span></th></tr></thead>
            <tbody>
              {dead.map((d) => (
                <tr key={d.submission_id}>
                  <th scope="row">{d.submission_id.slice(0, 8)}</th><td>{new Date(d.created_at).toLocaleString()}</td><td>{d.claim_count ?? '—'}</td>
                  <td><button className="btn btn-secondary" onClick={() => setTarget(d.submission_id)}>Retry<span className="visually-hidden"> attempt {d.submission_id.slice(0, 8)}</span></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <ConfirmDialog open={!!target} title="Retry this attempt?" confirmLabel="Put back in the queue" onCancel={() => setTarget(null)} onConfirm={() => target && requeue.mutate(target)}>
        <p>Only do this once the worker is healthy. The attempt gets a fresh set of tries. Nothing was marked against the learner.</p>
      </ConfirmDialog>
    </section>
  );
}
