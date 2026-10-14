import { useQuery } from '@tanstack/react-query';
import { ErrorMessage, Loading } from '../../components/States';
import { errorMessage } from '../../services/api';
import { getAdminSettings } from '../../services/adminApi';

export function AdminSettings() {
  const q = useQuery({ queryKey: ['a-settings'], queryFn: getAdminSettings });
  if (q.isPending) return <Loading label="Loading settings…" />;
  if (q.isError) return <ErrorMessage message={errorMessage(q.error)} onRetry={() => void q.refetch()} />;
  return (
    <section aria-label="Settings">
      <p className="muted">These limits are set by the deployment and are shown here so you know what the platform enforces. Changing one is a reviewed configuration change, not a button, because a wrong value can take grading offline. No secrets are shown.</p>
      <div className="table-wrap">
        <table>
          <caption>Platform settings (read only)</caption>
          <thead><tr><th scope="col">Setting</th><th scope="col">Value</th><th scope="col">What it does</th></tr></thead>
          <tbody>{q.data.settings.map((s) => <tr key={s.label}><th scope="row">{s.label}</th><td>{s.value || '—'}</td><td>{s.note}</td></tr>)}</tbody>
        </table>
      </div>
      <h2>Backups and recovery</h2>
      <p>Take a backup before any schema or content change with <code>scripts/backup_db.py</code>; rehearse a restore with <code>scripts/dr_rehearsal.sh</code>. The full procedure is in <code>docs/06-operations/BACKUP_RESTORE_RUNBOOK.md</code>. Backups are run by an administrator on a trusted machine, not from this page.</p>
    </section>
  );
}
