import { Icon } from '../../components/Icon';
import type { Segment } from '../../services/types';
import type { TimelineState } from './timeline';

const ICON: Record<Segment['type'], string> = { video: 'video', checkpoint: 'quiz', exercise: 'code', exit_check: 'flag' };
const KIND: Record<Segment['type'], string> = { video: 'Video', checkpoint: 'Knowledge check', exercise: 'Practical lab', exit_check: 'Exit check' };

function stepState(state: TimelineState, i: number): 'done' | 'current' | 'upcoming' {
  if (state.phase === 'completed' || i < state.index) return 'done';
  return i === state.index ? 'current' : 'upcoming';
}

/** Horizontal stage stepper: where you are in the lesson at a glance. */
export function Stepper({ state }: { state: TimelineState }) {
  return (
    <ol className="stepper" aria-label="Lesson stages">
      {state.segments.map((s, i) => {
        const st = stepState(state, i);
        return (
          <li key={s.id} className={`step ${st}`} aria-current={st === 'current' ? 'step' : undefined}>
            <Icon name={st === 'done' ? 'check' : ICON[s.type]} size={16} />
            <span>{KIND[s.type]}</span>
            <span className="visually-hidden">({st === 'done' ? 'done' : st === 'current' ? 'current' : 'upcoming'})</span>
          </li>
        );
      })}
    </ol>
  );
}

export function Outline({ state }: { state: TimelineState }) {
  return (
    <ol className="outline">
      {state.segments.map((s, i) => {
        const st = stepState(state, i);
        return (
          <li key={s.id} aria-current={st === 'current' ? 'step' : undefined} className={st === 'current' ? 'current' : ''}>
            <span aria-hidden="true">{st === 'done' ? '✓' : st === 'current' ? '▶' : '○'}</span>
            <span>{s.title} <span className="muted">({st === 'done' ? 'done' : st === 'current' ? 'current' : 'upcoming'})</span></span>
          </li>
        );
      })}
    </ol>
  );
}
