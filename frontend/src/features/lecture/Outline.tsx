import type { TimelineState } from './timeline';

export function Outline({ state }: { state: TimelineState }) {
  return (
    <ol className="outline">
      {state.segments.map((s, i) => {
        const done = state.phase === 'completed' || i < state.index;
        const current = i === state.index && state.phase !== 'completed';
        return (
          <li key={s.id} aria-current={current ? 'step' : undefined} className={current ? 'current' : ''}>
            <span aria-hidden="true">{done ? '✓' : current ? '▶' : '○'}</span>{' '}
            {s.title} <span className="muted">({done ? 'done' : current ? 'current' : 'upcoming'})</span>
          </li>
        );
      })}
    </ol>
  );
}
