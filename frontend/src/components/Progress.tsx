/** Progress is always shown with text (value/total) in addition to the bar. */
export function ProgressBar({ label, done, total, tone = 'primary' }: { label: string; done: number; total: number; tone?: 'primary' | 'success' }) {
  const pct = total > 0 ? Math.round((100 * done) / total) : 0;
  return (
    <div className="pbar">
      <div className="pbar-head"><span>{label}</span><span>{done} of {total}</span></div>
      <div className="pbar-track" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={total} aria-valuenow={done} aria-valuetext={`${done} of ${total}`}>
        <div className={`pbar-fill pbar-${tone}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function ProgressRing({ done, total, label }: { done: number; total: number; label: string }) {
  const pct = total > 0 ? done / total : 0;
  const r = 34;
  const c = 2 * Math.PI * r;
  return (
    <figure className="ring" aria-label={`${label}: ${done} of ${total}`}>
      <svg width="88" height="88" viewBox="0 0 88 88" aria-hidden="true">
        <circle cx="44" cy="44" r={r} className="ring-bg" />
        <circle cx="44" cy="44" r={r} className="ring-fg" strokeDasharray={c} strokeDashoffset={c * (1 - pct)} transform="rotate(-90 44 44)" />
      </svg>
      <figcaption><strong>{done}<small>/{total}</small></strong><span>{label}</span></figcaption>
    </figure>
  );
}
