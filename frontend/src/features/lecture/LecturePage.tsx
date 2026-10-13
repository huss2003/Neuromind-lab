import { Suspense, lazy, useCallback, useEffect, useReducer, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Badge, type BadgeKind } from '../../components/Badge';
import { McqCheckpoint } from '../../components/McqCheckpoint';
import { ProgressBar } from '../../components/Progress';
import { ErrorMessage, Loading } from '../../components/States';
import { VideoSegment } from '../../components/VideoSegment';
import { ApiError, errorMessage } from '../../services/api';
import { completeLecture, getManifest, getSession, saveSession, submitAnswer } from '../../services/lectureApi';
import type { Manifest, Progress } from '../../services/types';
import { Outline, Stepper } from './Outline';
import { canLeaveExercise, continueFromExercise, initialState, isMediaSegment, isTextSegment, timelineReducer, type TimelineEvent, type TimelineState } from './timeline';

const ExerciseLab = lazy(() => import('../lab/ExerciseLab').then((m) => ({ default: m.ExerciseLab })));

type Save = 'idle' | 'saving' | 'saved' | 'error';

const STATE_BADGE: Record<string, [BadgeKind, string]> = {
  NOT_STARTED: ['neutral', 'Not started'], IN_PROGRESS: ['info', 'In progress'], GRADING_PENDING: ['info', 'Grading in progress'],
  REMEDIATION_REQUIRED: ['warning', 'Needs work — see guidance'], COMPLETED: ['success', 'Completed'],
};

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
  const [progress, setProgress] = useState<Progress | null>(null);
  const [lectureState, setLectureState] = useState<string>('IN_PROGRESS');
  const [oriented, setOriented] = useState(false);
  const [blocked, setBlocked] = useState<string | null>(null);
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
      setProgress(s.progress);
      setLectureState(s.lecture_state ?? 'IN_PROGRESS');
      setOriented(s.lecture_state !== 'NOT_STARTED');
      dispatch({
        type: 'LOADED', segments: m.segments, currentSegmentId: s.current_segment_id, results: s.checkpoint_results,
        completedExercises: s.completed_exercise_ids, completed: s.status === 'completed',
      });
    } catch (e) {
      if (e instanceof ApiError && e.code === 'LECTURE_LOCKED') setBlocked(e.message);
      else setLoadError(e instanceof ApiError && e.status === 404 ? 'This lecture was not found, is not published, or is not part of a course you are enrolled in.' : errorMessage(e));
    }
  }, [lectureId]);
  useEffect(() => { void load(); }, [load]);

  const segment = state.segments[state.index];

  const refreshProgress = useCallback(() => {
    getSession(lectureId).then((s) => { setProgress(s.progress); setLectureState(s.lecture_state ?? 'IN_PROGRESS'); }).catch(() => undefined); // display only; failure is harmless
  }, [lectureId]);

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
      setProgress(s.progress);
      setSave('saved');
    } catch {
      setSave('error');
    }
  }, [lectureId]);

  // Persist on every segment change (the server validates the move against required checkpoints).
  useEffect(() => {
    if (!segment || state.phase === 'loading' || state.phase === 'completed' || state.phase === 'recoverable_error') return;
    if (lastPersisted.current !== segment.id) { setStartAt(0); void persist(segment.id, 0); }
  }, [segment, state.phase, persist]);

  // Server-validated completion once the exit check is done.
  useEffect(() => {
    if (state.phase !== 'finishing') return;
    completeLecture(lectureId)
      .then((s) => { setProgress(s.progress); dispatch({ type: 'COMPLETION_CONFIRMED' }); })
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
      refreshProgress();
    } catch (e) {
      dispatch({ type: 'ANSWER_FAILED', message: errorMessage(e) });
    }
  }

  if (blocked) return (
    <main className="page narrow">
      <h1>This lecture is locked</h1>
      <div role="alert" className="notice notice-warning"><p>{blocked}</p></div>
      <Link className="btn btn-primary" to="/">Back to dashboard</Link>
    </main>
  );
  if (loadError) return <main className="page"><ErrorMessage message={loadError} onRetry={() => void load()} /><p><Link to="/">Back to dashboard</Link></p></main>;
  if (!manifest || state.phase === 'loading') return <main className="page"><Loading label="Loading lecture…" /></main>;

  const inPlay = state.phase !== 'recoverable_error' && state.phase !== 'finishing' && state.phase !== 'completed';
  if (!oriented && state.phase !== 'completed') return <Orientation manifest={manifest} onStart={() => setOriented(true)} />;
  return (
    <main className="page lecture">
      <nav className="crumbs" aria-label="Breadcrumb"><Link to="/">Dashboard</Link> <span aria-hidden="true">›</span> <span aria-current="page">Lecture {manifest.lecture_number}</span></nav>
      <h1>Lecture {manifest.lecture_number}: {manifest.title}</h1>
      <p>{STATE_BADGE[lectureState] && <Badge kind={STATE_BADGE[lectureState][0]}>{STATE_BADGE[lectureState][1]}</Badge>}</p>
      <Stepper state={state} />
      <div className="lecture-grid">
        <div>
          {state.phase === 'recoverable_error' && (
            <div className="card" role="alert">
              <h2>{state.errorKind === 'media' ? 'The video had a problem' : state.errorKind === 'content' ? 'This lecture needs attention' : 'Connection problem'}</h2>
              <p>{state.error}</p>
              {state.errorKind === 'media' && <p>Your progress is safe. Retry the video, or continue without it.</p>}
              {state.errorKind === 'content' && <p>This isn't something you did. Please tell your teacher.</p>}
              <div className="actions">
                {state.errorKind !== 'content' && <button className="btn btn-primary" onClick={() => dispatch({ type: 'RECOVER' })}>Try again</button>}
                {state.errorKind === 'media' && segment && (
                  <button className="btn btn-secondary" onClick={() => { dispatch({ type: 'RECOVER' }); dispatch({ type: 'VIDEO_ENDED', segmentId: segment.id }); }}>Continue without video</button>
                )}
              </div>
            </div>
          )}

          {segment && isTextSegment(segment) && inPlay && (
            <section className="card" aria-labelledby="text-title">
              <p className="muted">{segment.type === 'intro' ? 'Introduction' : segment.type === 'reflection' ? 'Reflection' : 'Reading'}</p>
              <h2 id="text-title">{segment.title}</h2>
              <p className="reading">{segment.body}</p>
              <button className="btn btn-primary" onClick={() => dispatch({ type: 'SECTION_DONE', segmentId: segment.id })}>Continue</button>
            </section>
          )}

          {segment && isMediaSegment(segment) && inPlay && (
            <VideoSegment
              segment={segment} startAt={startAt}
              onPlay={() => dispatch({ type: 'PLAY' })} onPause={() => dispatch({ type: 'PAUSE' })}
              onEnded={() => dispatch({ type: 'VIDEO_ENDED', segmentId: segment.id })}
              onError={() => dispatch({ type: 'MEDIA_ERROR', segmentId: segment.id })}
              onPosition={(t) => void persist(segment.id, t)}
            />
          )}

          {segment && (segment.type === 'checkpoint' || segment.type === 'exit_check') && inPlay && (
            <McqCheckpoint
              segment={segment} isExitCheck={segment.type === 'exit_check'}
              result={segment.checkpoint ? state.results[segment.checkpoint.id] : undefined}
              submitting={state.phase === 'submitting_answer'}
              onSubmit={(o) => void onAnswer(o)}
              onContinue={() => dispatch({ type: 'CONTINUE' })}
              onRetry={() => dispatch({ type: 'RETRY_ANSWER' })}
            />
          )}

          {segment && segment.type === 'exercise' && segment.exercise_id && inPlay && (
            <Suspense fallback={<Loading label="Loading the coding lab…" />}>
            <ExerciseLab
              key={segment.exercise_id} exerciseId={segment.exercise_id} sections={state.segments}
              alreadyPassed={canLeaveExercise(state)}
              onGradingStart={() => dispatch({ type: 'GRADING_STARTED' })}
              onGradingEnd={(sub) => {
                dispatch({ type: 'GRADING_FINISHED', passed: sub.status === 'passed' });
                if (sub.status === 'passed' && segment.exercise_id) dispatch({ type: 'EXERCISE_PASSED', exerciseId: segment.exercise_id });
                refreshProgress();
              }}
              onContinue={() => dispatch({ type: 'LEAVE_EXERCISE' })}
            />
            </Suspense>
          )}

          {state.phase === 'finishing' && <div className="card"><Loading label="Checking that everything is complete…" /></div>}
          {state.phase === 'completed' && <CompletionSummary manifest={manifest} progress={progress} />}

          <p className="muted" aria-live="polite">
            {save === 'saving' && 'Saving progress…'}
            {save === 'saved' && 'Progress saved'}
            {save === 'error' && <>Could not save your progress. <button className="btn btn-tertiary" onClick={() => segment && void persist(segment.id, 0)}>Retry saving</button></>}
          </p>
        </div>

        <aside aria-label="Lesson progress">
          <div className="card">
            <h2>Your progress</h2>
            {progress && (
              <>
                <ProgressBar label="Videos watched" done={progress.media.done} total={progress.media.total} />
                <ProgressBar label="Knowledge checks" done={progress.checkpoints.done} total={progress.checkpoints.total} />
                <ProgressBar label="Practical labs passed" done={progress.labs.done} total={progress.labs.total} />
                <p className="muted" style={{ marginBottom: 0 }}>
                  Mastery: {progress.mastery.lecture_completed ? 'lecture completed' : progress.mastery.best_exercise_score != null ? `best lab score ${progress.mastery.best_exercise_score}% (pass mark ${progress.mastery.pass_mark}%)` : 'not yet assessed'}
                </p>
              </>
            )}
          </div>
          <div className="card">
            <h2>Lesson outline</h2>
            <Outline state={state} />
          </div>
          {manifest.learning_objectives.length > 0 && (
            <details className="card" open>
              <summary><strong>Objectives</strong></summary>
              <ul>{manifest.learning_objectives.map((o) => <li key={o}>{o}</li>)}</ul>
            </details>
          )}
        </aside>
      </div>
    </main>
  );
}

function CompletionSummary({ manifest, progress }: { manifest: Manifest; progress: Progress | null }) {
  return (
    <section className="card" aria-labelledby="done-title">
      <h2 id="done-title"><Badge kind="success">Completed</Badge> Lecture complete</h2>
      <p>You finished <strong>Lecture {manifest.lecture_number}: {manifest.title}</strong>. Your progress has been saved to your account.</p>
      {progress && (
        <ul>
          <li>Videos: {progress.media.done} of {progress.media.total}</li>
          <li>Knowledge checks: {progress.checkpoints.done} of {progress.checkpoints.total}</li>
          <li>Practical labs passed: {progress.labs.done} of {progress.labs.total}</li>
          {progress.mastery.best_exercise_score != null && <li>Best lab score: {progress.mastery.best_exercise_score}%</li>}
        </ul>
      )}
      <div className="actions">
        <Link className="btn btn-primary" to="/">Back to dashboard</Link>
        <Link className="btn btn-secondary" to="/progress">See all my progress</Link>
      </div>
    </section>
  );
}


function Orientation({ manifest, onStart }: { manifest: Manifest; onStart: () => void }) {
  return (
    <main className="page narrow">
      <nav className="crumbs" aria-label="Breadcrumb"><Link to="/">Dashboard</Link> <span aria-hidden="true">›</span> <span aria-current="page">Lecture {manifest.lecture_number}</span></nav>
      <h1>Lecture {manifest.lecture_number}: {manifest.title}</h1>
      <section className="card" aria-labelledby="orient-title">
        <h2 id="orient-title">Before you start</h2>
        {manifest.summary && <p>{manifest.summary}</p>}
        <dl className="facts">
          {manifest.estimated_minutes != null && (<><dt>Estimated time</dt><dd>About {manifest.estimated_minutes} minutes</dd></>)}
          <dt>Prerequisites</dt>
          <dd>{manifest.prerequisites.length === 0 ? 'None — you can start right away.' : manifest.prerequisites.map((p) => p.title).join(', ')}</dd>
        </dl>
        {manifest.learning_objectives.length > 0 && (<><h3>What you will learn</h3><ul>{manifest.learning_objectives.map((o) => <li key={o}>{o}</li>)}</ul></>)}
        {manifest.completion_criteria.length > 0 && (<><h3>How this lecture is completed</h3><ul>{manifest.completion_criteria.map((c) => <li key={c}>{c}</li>)}</ul></>)}
        {manifest.attempt_policy && <p className="muted">{manifest.attempt_policy}</p>}
        <div className="actions"><button className="btn btn-primary" onClick={onStart}>Start lecture</button><Link className="btn btn-secondary" to="/">Not now</Link></div>
      </section>
    </main>
  );
}
