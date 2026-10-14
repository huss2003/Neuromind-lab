import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Badge } from '../../components/Badge';
import { ErrorMessage, Loading } from '../../components/States';
import { errorMessage } from '../../services/api';
import { getAdminOverview } from '../../services/adminApi';

const secs = (v: number | null | undefined) => (v === null || v === undefined ? '—' : `${v.toFixed(1)} s`);

export function AdminOverview() {
  const q = useQuery({ queryKey: ['a-overview'], queryFn: getAdminOverview, refetchInterval: 30_000 });
  if (q.isPending) return <Loading label="Loading system overview…" />;
  if (q.isError) return <ErrorMessage message={errorMessage(q.error)} onRetry={() => void q.refetch()} />;
  const o = q.data;
  const g = o.grading_24h;
  const tiles: [string, string | number, string][] = [
    ['Learners', o.users.learners, `${o.users.deactivated} deactivated account${o.users.deactivated === 1 ? '' : 's'}`],
    ['Teachers and administrators', o.users.teachers + o.users.admins, `${o.users.teachers} teachers, ${o.users.admins} administrators`],
    ['Lectures published', o.content.lectures_published, `of ${o.content.lectures_total} in the database`],
    ['Waiting to be graded', o.queue.queued, o.queue.oldest_queued_seconds === null ? 'nothing waiting' : `oldest has waited ${o.queue.oldest_queued_seconds} s`],
    ['Being graded now', o.queue.running, 'jobs held by a worker'],
    ['Open issue reports', o.open_issues, 'from learners and teachers'],
  ];
  return (
    <section aria-label="System overview">
      <div className="grid grid-3">
        {tiles.map(([label, value, hint]) => <div key={label} className="tile"><strong>{value}</strong><span className="tile-label">{label}</span><span className="tile-hint">{hint}</span></div>)}
      </div>
      <h2>Service health</h2>
      <ul className="status-list">
        <li><Badge kind={o.health.api ? 'success' : 'danger'}>{o.health.api ? 'Online' : 'Offline'}</Badge> API</li>
        <li><Badge kind={o.health.database ? 'success' : 'danger'}>{o.health.database ? 'Online' : 'Offline'}</Badge> Database</li>
        <li><Badge kind={o.queue.running > 0 || o.queue.queued === 0 ? 'success' : 'warning'}>{o.queue.queued > 0 && o.queue.running === 0 ? 'Check worker' : 'Working'}</Badge> Grading worker (judged from the queue; CloudWatch alarms watch the host)</li>
      </ul>
      <p className="muted">Checked {new Date(o.health.checked_at).toLocaleTimeString()}. This page refreshes every 30 seconds.</p>
      <h2>Grading in the last 24 hours</h2>
      <p>{g.sample} attempt{g.sample === 1 ? '' : 's'} measured. Queue wait median {secs(g.queue_wait_seconds.p50)}, 95th percentile {secs(g.queue_wait_seconds.p95)}. Execution median {secs(g.execution_seconds.p50)}, 95th percentile {secs(g.execution_seconds.p95)}.</p>
      {o.dead_letters > 0 && (
        <div role="alert" className="notice notice-warning">
          <strong>{o.dead_letters} attempt{o.dead_letters === 1 ? '' : 's'} could not be graded.</strong>
          <p>These were not marked against the learner. <Link to="/admin/queue">Review the grading queue</Link> to retry them.</p>
        </div>
      )}
    </section>
  );
}
