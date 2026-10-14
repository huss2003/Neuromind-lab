import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { EmptyState, ErrorMessage, Loading } from '../components/States';
import { errorMessage } from '../services/api';
import { getPortfolio, removePortfolio, type PortfolioItem } from '../services/adminApi';

export function Portfolio() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ['portfolio'], queryFn: getPortfolio });
  const [target, setTarget] = useState<PortfolioItem | null>(null);
  const remove = useMutation({ mutationFn: (id: string) => removePortfolio(id), onSuccess: () => { setTarget(null); void qc.invalidateQueries({ queryKey: ['portfolio'] }); } });
  return (
    <main className="page narrow">
      <h1>Portfolio</h1>
      <p className="muted">Your best work, chosen by you. Only submissions that passed official grading can be added, so each piece is proven. Add one from the results panel after a lab passes.</p>
      {q.isPending && <Loading label="Loading your portfolio…" />}
      {q.isError && <ErrorMessage message={errorMessage(q.error)} onRetry={() => void q.refetch()} />}
      {q.data?.length === 0 && <EmptyState title="Nothing here yet">Pass a lab, then choose “Add to portfolio” on the result.</EmptyState>}
      {q.data?.map((it) => (
        <section key={it.id} className="card" aria-labelledby={`pf-${it.id}`}>
          <h2 id={`pf-${it.id}`} style={{ marginTop: 0 }}>{it.title}</h2>
          <p className="muted">{it.exercise ?? 'Lab'} · official score {it.score ?? '—'}% · added {new Date(it.created_at).toLocaleDateString()}</p>
          {it.note && <p>{it.note}</p>}
          <pre className="code" tabIndex={0} aria-label={`Code for ${it.title}`}>{it.source_code}</pre>
          <button className="btn btn-tertiary" onClick={() => setTarget(it)}>Remove<span className="visually-hidden"> {it.title}</span></button>
        </section>
      ))}
      <ConfirmDialog open={!!target} title={`Remove “${target?.title ?? ''}”?`} confirmLabel="Remove" destructive onCancel={() => setTarget(null)} onConfirm={() => target && remove.mutate(target.id)}>
        <p>It leaves your portfolio. Your official attempt and score are not affected.</p>
      </ConfirmDialog>
    </main>
  );
}
