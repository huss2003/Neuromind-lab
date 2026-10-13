import { describe, expect, it } from 'vitest';
import type { CheckpointResult, Segment } from '../../services/types';
import { canLeaveExercise, continueFromExercise, initialState, progressPercent, timelineReducer as r, type TimelineEvent, type TimelineState } from './timeline';

const q = { id: 'q', prompt: 'P', options: [{ id: 'a', text: 'A' }] };
const base = { required: true, next_action: { type: 'next_segment' } };
const segs: Segment[] = [
  { ...base, id: 'v1', order: 1, type: 'video', title: 'Intro', media: { provider: null, url: 'x' } },
  { ...base, id: 'c1', order: 2, type: 'checkpoint', title: 'K1', checkpoint: { id: 'cp1', type: 'mcq', required: true, question: q } },
  { ...base, id: 'v2', order: 3, type: 'video', title: 'Practical', media: { provider: null, url: 'y' }, next_action: { type: 'open_exercise', exercise_id: 'ex1' } },
  { ...base, id: 'x1', order: 4, type: 'exercise', title: 'Lab', exercise_id: 'ex1' },
  { ...base, id: 'e1', order: 5, type: 'exit_check', title: 'Exit', checkpoint: { id: 'cp2', type: 'exit_check', required: true, question: q } },
];
const result = (completed: boolean): CheckpointResult => ({ attempt_id: 'a', is_correct: completed, score: completed ? 1 : 0, explanation: 'why', checkpoint_completed: completed });

function run(events: TimelineEvent[], from: TimelineState = initialState) {
  return events.reduce(r, from);
}
const load = (id: string | null = 'v1', extra: Partial<Extract<TimelineEvent, { type: 'LOADED' }>> = {}): TimelineEvent => ({
  type: 'LOADED', segments: segs, currentSegmentId: id, results: {}, completedExercises: [], completed: false, ...extra,
});

describe('timeline', () => {
  it('loads at the saved segment (resume) and chooses phase by segment type', () => {
    expect(run([load('v1')]).phase).toBe('ready');
    expect(run([load('c1')]).phase).toBe('awaiting_checkpoint');
    expect(run([load('x1')]).phase).toBe('exercise');
    expect(run([load('c1', { results: { cp1: result(true) } })]).phase).toBe('showing_result');
    expect(run([load('nope')]).index).toBe(0);
  });

  it('empty lecture is a content error, never a silent completion', () => {
    const s = run([{ type: 'LOADED', segments: [], currentSegmentId: null, results: {}, completedExercises: [], completed: false }]);
    expect(s.phase).toBe('recoverable_error');
    expect(s.errorKind).toBe('content');
  });

  it('video end advances exactly once even when `ended` fires twice', () => {
    const once = run([load(), { type: 'PLAY' }, { type: 'VIDEO_ENDED', segmentId: 'v1' }]);
    expect(once.index).toBe(1);
    expect(once.phase).toBe('awaiting_checkpoint');
    const twice = r(once, { type: 'VIDEO_ENDED', segmentId: 'v1' });
    expect(twice).toBe(once);
  });

  it('ignores ended events from the wrong segment', () => {
    const s = run([load(), { type: 'PLAY' }, { type: 'VIDEO_ENDED', segmentId: 'v2' }]);
    expect(s.index).toBe(0);
  });

  it('checkpoint flow: submit -> result -> continue only when server completed it', () => {
    let s = run([load('c1'), { type: 'SUBMIT_ANSWER' }]);
    expect(s.phase).toBe('submitting_answer');
    s = r(s, { type: 'ANSWER_RESULT', checkpointId: 'cp1', result: result(false) });
    expect(s.phase).toBe('showing_result');
    expect(r(s, { type: 'CONTINUE' })).toBe(s); // not unlocked
    s = r(s, { type: 'RETRY_ANSWER' });
    expect(s.phase).toBe('awaiting_checkpoint');
    s = run([{ type: 'SUBMIT_ANSWER' }, { type: 'ANSWER_RESULT', checkpointId: 'cp1', result: result(true) }, { type: 'CONTINUE' }], s);
    expect(s.index).toBe(2);
    expect(s.phase).toBe('ready');
  });

  it('API failure while submitting shows recoverable error and does not unlock', () => {
    let s = run([load('c1'), { type: 'SUBMIT_ANSWER' }, { type: 'ANSWER_FAILED', message: 'offline' }]);
    expect(s.phase).toBe('recoverable_error');
    expect(s.errorKind).toBe('api');
    s = r(s, { type: 'RECOVER' });
    expect(s.phase).toBe('awaiting_checkpoint');
    expect(s.results.cp1).toBeUndefined();
  });

  it('answer results are ignored unless an answer is in flight', () => {
    const s = run([load('c1')]);
    expect(r(s, { type: 'ANSWER_RESULT', checkpointId: 'cp1', result: result(true) })).toBe(s);
  });

  it('practical video end opens its explicit exercise (not "next in order")', () => {
    const s = run([load('v2'), { type: 'VIDEO_ENDED', segmentId: 'v2' }]);
    expect(s.segments[s.index].id).toBe('x1');
    expect(s.phase).toBe('exercise');
  });

  it('missing exercise link is a content error, not a completion', () => {
    const broken = segs.filter((x) => x.id !== 'x1');
    const s = run([{ type: 'LOADED', segments: broken, currentSegmentId: 'v2', results: {}, completedExercises: [], completed: false }, { type: 'VIDEO_ENDED', segmentId: 'v2' }]);
    expect(s.phase).toBe('recoverable_error');
    expect(s.errorKind).toBe('content');
    expect(r(s, { type: 'RECOVER' })).toBe(s);
  });

  it('exercise cannot be left until the server confirms a pass; failed grading shows remediation', () => {
    let s = run([load('x1'), { type: 'GRADING_STARTED' }]);
    expect(s.phase).toBe('awaiting_grading');
    s = r(s, { type: 'GRADING_FINISHED', passed: false });
    expect(s.phase).toBe('showing_remediation');
    expect(continueFromExercise(s)).toBe(s);
    s = run([{ type: 'GRADING_STARTED' }, { type: 'GRADING_FINISHED', passed: true }, { type: 'EXERCISE_PASSED', exerciseId: 'ex1' }], s);
    expect(canLeaveExercise(s)).toBe(true);
    expect(continueFromExercise(s).segments[continueFromExercise(s).index].id).toBe('e1');
  });

  it('exit check leads to server-validated completion; rejection is recoverable', () => {
    let s = run([load('e1'), { type: 'SUBMIT_ANSWER' }, { type: 'ANSWER_RESULT', checkpointId: 'cp2', result: result(true) }, { type: 'CONTINUE' }]);
    expect(s.phase).toBe('finishing');
    s = r(s, { type: 'COMPLETION_REJECTED', message: 'not met' });
    expect(s.phase).toBe('recoverable_error');
    s = run([load('e1'), { type: 'SUBMIT_ANSWER' }, { type: 'ANSWER_RESULT', checkpointId: 'cp2', result: result(true) }, { type: 'CONTINUE' }, { type: 'COMPLETION_CONFIRMED' }]);
    expect(s.phase).toBe('completed');
    expect(progressPercent(s)).toBe(100);
  });

  it('media error is recoverable and never advances', () => {
    const s = run([load(), { type: 'MEDIA_ERROR', segmentId: 'v1' }]);
    expect(s.phase).toBe('recoverable_error');
    expect(s.index).toBe(0);
    expect(r(s, { type: 'RECOVER' }).phase).toBe('ready');
  });

  it('completed lectures reopen in the completed phase', () => {
    expect(run([load('e1', { completed: true })]).phase).toBe('completed');
  });
});
