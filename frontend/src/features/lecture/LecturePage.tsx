import { useCallback, useEffect, useReducer, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Badge } from '../../components/Badge';
import { McqCheckpoint } from '../../components/McqCheckpoint';
import { ErrorMessage, Loading } from '../../components/States';
import { VideoSegment } from '../../components/VideoSegment';
import { ApiError, errorMessage } from '../../services/api';
import { completeLecture, getManifest, getSession, saveSession, submitAnswer } from '../../services/lectureApi';
import type { Manifest } from '../../services/types';
import { ExerciseLab } from '../lab/ExerciseLab';
import { Outline } from './Outline';
import { canLeaveExercise, continueFromExercise, initialState, progressPercent, timelineReducer, type TimelineEvent, type TimelineState } from './timeline';

type Save = 'idle' | 'saving' | 'saved' | 'error';

function reducer(s: TimelineState, e: TimelineEvent | { type: 'LEAVE_EXERCISE' }): TimelineState {
  return e.type === 'LEAVE_EXERCISE' ? continueFromExercise(s) : timelineReducer(s, e);
}

export function LecturePage() {
  const { lectureId = '' } = useParams();
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [state, dispatch] = useReducer(reducer, initialState);
  const [save, setSave] = useState<Save>('idle');
  const [startAt, setStartAt] = useState(0);
  const version = useRef(1);
  const answerKey = useRef<{ id: string; key: string } | null>(null);
  const lastPersisted = useRef<string | null>(null);

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      const [m, s] = await Promise.all([getManifest(lectureId), getSession(lectureId)]);
      setManifest(m);
      version.current = s.state_version;
      lastPersisted.current = s.current_segment_id;
      setStartAt(s.playback_position_seconds);
      dispatch({
        type: 'LOADED', segments: m.segments, currentSegmentId: s.current_segment_id, results: s.checkpoint_results,
        completedExercises: s.completed_exercise_ids, completed: s.status === 'completed',
      });
    } catch (e) {
      setLoadError(e instanceof ApiError && e.status === 404 ? 'This lecture was not found or is not published.' : errorMessage(e));
    }
  }, [lectureId]);
  useEffect(() => { void load(); }, [load]);

  const segment = state.segments[state.index];

  const persist = useCallback(async (segmentId: string, position: number) => {
    setSave('saving');
    try {
      let s;
      try {
        s = await saveSession(lectureId, segmentId, position, version.current);
      } catch (e) {
        if (e instanceof ApiError && e.status === 409) { // another tab moved on: take the latest version and retry once
          version.current = (await getSession(lectureId)).state_version;
          s = await saveSession(lectureId, segmentId, position, version.current);
        } else throw e;
      }
      version.current = s.state_version;
      lastPersisted.current = segmentId;
      setSave('saved');
    } catch {
      setSave('error');
    }
  }, [lectureId]);

  // Persist on every segment change (server validates the move against required checkpoints).
  useEffect(() => {
    if (!segment || state.phase === 'loading' || state.phase === 'completed' || state.phase === 'recoverable_error') return;
    if (lastPersisted.current !== segment.id) { setStartAt(0); void persist(segment.id, 0); }
  }, [segment, state.phase, persist]);

  // Server-validated completion once the exit check is done.
  useEffect(() => {
    if (state.phase !== 'finishing') return;
    completeLecture(lectureId)
      .then(() => dispatch({ type: 'COMPLETION_CONFIRMED' }))
      .catch((e) => dispatch({ type: 'COMPLETION_REJECTED', message: errorMessage(e) }));
  }, [state.phase, lectureId]);

  async function onAnswer(optionId: string) {
    const cp = segment?.checkpoint;
    if (!cp) return;
    const id = `${cp.id}:${optionId}`;
    if (answerKey.current?.id !== id) answerKey.current = { id, key: crypto.randomUUID() };
    dispatch({ type: 'SUBMIT_ANSWER' });
    try {
      const result = await submitAnswer(cp.id, cp.question.id, optionId, answerKey.current.key);
      answerKey.current = null;
      dispatch({ type: 'ANSWER_RESULT', checkpointId: cp.id, result });
    } catch (e) {
      dispatch({ type: 'ANSWER_FAILED', message: errorMessage(e) });
    }
  }

  if (loadError) return <main><ErrorMessage message={loadError} /><p><button className="btn btn-secondary" onClick={() => void load()}>Retry</button> <Link to="/">Back to dashboard</Link></p></main>;
  if (!manifest || state.phase === 'loading') return <Loading label="Loading lecture…" />;

  return (
    <main className="lecture">
      <nav aria-label="Breadcrumb"><Link to="/">Dashboard</Link> › Lecture {manifest.lecture_number}</nav>
      <h1>Lecture {manifest.lecture_number}: {manifest.title}</h1>
      <div className="lecture-grid">
        <div>
          {state.phase === 'recoverable_error' && (
            <div className="card" role="alert">
              <h2>{state.errorKind === 'media' ? 'Video problem' : state.errorKind === 'content' ? 'Lecture setup problem' : 'Connection problem'}</h2>
              <p>{state.error}</p>
              {state.errorKind === 'media' && <p>Your progress is safe. Retry the video, or continue without it.</p>}
              {state.errorKind !== 'content' && <button className="btn btn-primary" onClick={() => dispatch({ type: 'RECOVER' })}>Try again</button>}
              {state.errorKind === 'media' && segment && (
                <button className="btn btn-secondary" onClick={() => { dispatch({ type: 'RECOVER' }); dispatch({ type: 'VIDEO_ENDED', segmentId: segment.id }); }}>Continue without video</button>
              )}
            </div>
          )}

          {segment && segment.type === 'video' && state.phase !== 'recoverable_error' && (
            <VideoSegment
              segment={segment} startAt={startAt}
              onPlay={() => dispatch({ type: 'PLAY' })} onPause={() => dispatch({ type: 'PAUSE' })}
              onEnded={() => dispatch({ type: 'VIDEO_ENDED', segmentId: segment.id })}
              onError={() => dispatch({ type: 'MEDIA_ERROR', segmentId: segment.id })}
              onPosition={(t) => void persist(segment.id, t)}
            />
          )}

          {segment && (segment.type === 'checkpoint' || segment.type === 'exit_check') && state.phase !== 'recoverable_error' && state.phase !== 'finishing' && state.phase !== 'completed' && (
            <McqCheckpoint
              segment={segment} isExitCheck={segment.type === 'exit_check'}
              result={segment.checkpoint ? state.results[segment.checkpoint.id] : undefined}
              submitting={state.phase === 'submitting_answer'}
              onSubmit={(o) => void onAnswer(o)}
              onContinue={() => dispatch({ type: 'CONTINUE' })}
              onRetry={() => dispatch({ type: 'RETRY_ANSWER' })}
            />
          )}

          {segment && segment.type === 'exercise' && segment.exercise_id && state.phase !== 'recoverable_error' && state.phase !== 'finishing' && state.phase !== 'completed' && (
            <ExerciseLab
              key={segment.exercise_id} exerciseId={segment.exercise_id}
              alreadyPassed={canLeaveExercise(state)}
              onGradingStart={() => dispatch({ type: 'GRADING_STARTED' })}
              onGradingEnd={(sub) => {
                dispatch({ type: 'GRADING_FINISHED', passed: sub.status === 'passed' });
                if (sub.status === 'passed' && segment.exercise_id) dispatch({ type: 'EXERCISE_PASSED', exerciseId: segment.exercise_id });
              }}
              onContinue={() => dispatch({ type: 'LEAVE_EXERCISE' })}
            />
          )}

          {state.phase === 'finishing' && <Loading label="Checking that everything is complete…" />}
          {state.phase === 'completed' && (
            <section className="card" aria-labelledby="done-title">
              <h2 id="done-title"><Badge kind="success">Completed</Badge> Lecture complete</h2>
              <p>Your progress has been saved.</p>
              <Link className="btn btn-primary" to="/">Back to dashboard</Link>
            </section>
          )}

          <p className="muted" aria-live="polite">
            {save === 'saving' && 'Saving progress…'}
            {save === 'saved' && 'Progress saved'}
            {save === 'error' && <>Could not save your progress. <button className="btn btn-tertiary" onClick={() => segment && void persist(segment.id, 0)}>Retry saving</button></>}
          </p>
        </div>
        <aside aria-label="Lesson outline">
          <Outline state={state} />
          <p>Progress: {progressPercent(state)}%</p>
          {manifest.learning_objectives.length > 0 && (
            <details open><summary>Objectives</summary><ul>{manifest.learning_objectives.map((o) => <li key={o}>{o}</li>)}</ul></details>
          )}
        </aside>
      </div>
    </main>
  );
}
