/**
 * Lecture timeline state machine (pure, no I/O). The page feeds it events; effects (API calls,
 * media control) are derived from the resulting state. The server remains authoritative: this
 * module only decides what the UI shows next.
 */
import type { CheckpointResult, Segment } from '../../services/types';

export type Phase =
  | 'loading'
  | 'reading' // intro / reading / reflection section (no media)
  | 'ready' // video segment loaded, not yet playing
  | 'playing'
  | 'paused'
  | 'awaiting_checkpoint'
  | 'submitting_answer'
  | 'showing_result'
  | 'exercise' // exercise open (editing / practising)
  | 'awaiting_grading'
  | 'showing_remediation'
  | 'finishing' // requesting server-validated completion
  | 'completed'
  | 'recoverable_error';

export interface TimelineState {
  phase: Phase;
  segments: Segment[];
  index: number;
  results: Record<string, CheckpointResult>; // by checkpoint id
  completedExercises: string[];
  handledEndFor: string | null; // dedupes duplicate `ended` events
  error: string | null;
  errorKind: 'media' | 'api' | 'content' | null;
  errorFrom: Phase | null;
}

export type TimelineEvent =
  | { type: 'LOADED'; segments: Segment[]; currentSegmentId: string | null; results: Record<string, CheckpointResult>; completedExercises: string[]; completed: boolean }
  | { type: 'PLAY' }
  | { type: 'PAUSE' }
  | { type: 'VIDEO_ENDED'; segmentId: string }
  | { type: 'SECTION_DONE'; segmentId: string }
  | { type: 'MEDIA_ERROR'; segmentId: string }
  | { type: 'SUBMIT_ANSWER' }
  | { type: 'ANSWER_RESULT'; checkpointId: string; result: CheckpointResult }
  | { type: 'ANSWER_FAILED'; message: string }
  | { type: 'CONTINUE' }
  | { type: 'RETRY_ANSWER' }
  | { type: 'GRADING_STARTED' }
  | { type: 'GRADING_FINISHED'; passed: boolean }
  | { type: 'EXERCISE_PASSED'; exerciseId: string }
  | { type: 'COMPLETION_CONFIRMED' }
  | { type: 'COMPLETION_REJECTED'; message: string }
  | { type: 'RECOVER' };

export const initialState: TimelineState = {
  phase: 'loading', segments: [], index: 0, results: {}, completedExercises: [], handledEndFor: null,
  error: null, errorKind: null, errorFrom: null,
};

const cur = (s: TimelineState): Segment | undefined => s.segments[s.index];
const TEXT_TYPES: Segment['type'][] = ['intro', 'reading', 'example', 'reflection'];
/** A section plays media if it is a video, or any text-type section that was given a media URL. */
export const isMediaSegment = (seg: Segment | undefined): boolean => !!seg && (seg.type === 'video' || (TEXT_TYPES.includes(seg.type) && !!seg.media?.url));
export const isTextSegment = (seg: Segment | undefined): boolean => !!seg && TEXT_TYPES.includes(seg.type) && !isMediaSegment(seg);

/** Which phase a learner lands in when entering a segment (also used when resuming). */
export function phaseForSegment(seg: Segment | undefined, s: Pick<TimelineState, 'results' | 'completedExercises'>): Phase {
  if (!seg) return 'recoverable_error';
  if (isMediaSegment(seg)) return 'ready';
  if (isTextSegment(seg)) return 'reading';
  if (seg.type === 'exercise') return 'exercise';
  const r = seg.checkpoint ? s.results[seg.checkpoint.id] : undefined;
  return r ? 'showing_result' : 'awaiting_checkpoint';
}

function enter(s: TimelineState, index: number): TimelineState {
  const next = { ...s, index, handledEndFor: null, error: null, errorKind: null, errorFrom: null };
  return { ...next, phase: phaseForSegment(next.segments[index], next) };
}

function fail(s: TimelineState, kind: 'media' | 'api' | 'content', message: string): TimelineState {
  return { ...s, phase: 'recoverable_error', error: message, errorKind: kind, errorFrom: s.phase };
}

function advance(s: TimelineState): TimelineState {
  const seg = cur(s);
  if (!seg) return fail(s, 'content', 'This lecture has no content.');
  if (seg.type === 'exit_check' || s.index >= s.segments.length - 1) {
    return { ...s, phase: 'finishing' };
  }
  return enter(s, s.index + 1);
}

export function timelineReducer(s: TimelineState, e: TimelineEvent): TimelineState {
  const seg = cur(s);
  switch (e.type) {
    case 'LOADED': {
      if (e.segments.length === 0) return fail({ ...s, segments: [] }, 'content', 'This lecture has no segments yet.');
      const idx = Math.max(0, e.segments.findIndex((x) => x.id === e.currentSegmentId));
      const base: TimelineState = { ...initialState, segments: e.segments, results: e.results, completedExercises: e.completedExercises };
      if (e.completed) return { ...base, index: e.segments.length - 1, phase: 'completed' };
      return enter(base, idx);
    }
    case 'PLAY':
      return s.phase === 'ready' || s.phase === 'paused' ? { ...s, phase: 'playing' } : s;
    case 'PAUSE':
      return s.phase === 'playing' ? { ...s, phase: 'paused' } : s;
    case 'VIDEO_ENDED': {
      // Ignore stale/duplicate events: wrong segment, wrong phase, or already handled.
      if (!seg || !isMediaSegment(seg) || seg.id !== e.segmentId || s.handledEndFor === seg.id) return s;
      if (!['ready', 'playing', 'paused'].includes(s.phase)) return s;
      const handled = { ...s, handledEndFor: seg.id };
      if (seg.next_action.type === 'open_exercise') {
        const target = s.segments.findIndex((x) => x.type === 'exercise' && x.exercise_id === seg.next_action.exercise_id);
        if (target < 0) return fail(handled, 'content', 'The exercise for this video is not configured. Please tell your teacher.');
        return { ...enter(handled, target), handledEndFor: seg.id };
      }
      return advance(handled);
    }
    case 'SECTION_DONE': {
      if (!seg || !isTextSegment(seg) || seg.id !== e.segmentId || s.phase !== 'reading' || s.handledEndFor === seg.id) return s;
      return advance({ ...s, handledEndFor: seg.id });
    }
    case 'MEDIA_ERROR':
      if (!seg || seg.id !== e.segmentId || s.phase === 'recoverable_error') return s;
      return fail(s, 'media', 'The video could not be played.');
    case 'SUBMIT_ANSWER':
      return s.phase === 'awaiting_checkpoint' ? { ...s, phase: 'submitting_answer' } : s;
    case 'ANSWER_RESULT':
      if (s.phase !== 'submitting_answer') return s;
      return { ...s, phase: 'showing_result', results: { ...s.results, [e.checkpointId]: e.result } };
    case 'ANSWER_FAILED':
      return s.phase === 'submitting_answer' ? fail(s, 'api', e.message) : s;
    case 'RETRY_ANSWER': // exit check not yet passed: ask the question again
      return s.phase === 'showing_result' ? { ...s, phase: 'awaiting_checkpoint' } : s;
    case 'CONTINUE': {
      if (s.phase !== 'showing_result') return s;
      const r = seg?.checkpoint ? s.results[seg.checkpoint.id] : undefined;
      if (!r?.checkpoint_completed) return s; // server has not unlocked the next segment
      return advance(s);
    }
    case 'GRADING_STARTED':
      return s.phase === 'exercise' || s.phase === 'showing_remediation' ? { ...s, phase: 'awaiting_grading' } : s;
    case 'GRADING_FINISHED':
      if (s.phase !== 'awaiting_grading') return s;
      return { ...s, phase: e.passed ? 'exercise' : 'showing_remediation' };
    case 'EXERCISE_PASSED':
      return s.completedExercises.includes(e.exerciseId) ? s : { ...s, completedExercises: [...s.completedExercises, e.exerciseId] };
    case 'COMPLETION_CONFIRMED':
      return s.phase === 'finishing' ? { ...s, phase: 'completed' } : s;
    case 'COMPLETION_REJECTED':
      return s.phase === 'finishing' ? fail(s, 'api', e.message) : s;
    case 'RECOVER': {
      if (s.phase !== 'recoverable_error') return s;
      if (s.errorKind === 'content') return s;
      return { ...s, phase: s.errorFrom && s.errorFrom !== 'recoverable_error' ? (s.errorFrom === 'submitting_answer' ? 'awaiting_checkpoint' : s.errorFrom) : 'ready', error: null, errorKind: null };
    }
  }
}

/** Exercise segment becomes passable (Continue) only once the server confirms a pass. */
export function canLeaveExercise(s: TimelineState): boolean {
  const seg = cur(s);
  return seg?.type === 'exercise' && !!seg.exercise_id && s.completedExercises.includes(seg.exercise_id);
}

export function continueFromExercise(s: TimelineState): TimelineState {
  return canLeaveExercise(s) ? advance(s) : s;
}

export function progressPercent(s: TimelineState): number {
  if (s.segments.length === 0) return 0;
  if (s.phase === 'completed') return 100;
  return Math.round((100 * s.index) / s.segments.length);
}
