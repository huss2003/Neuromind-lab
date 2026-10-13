import Editor from '@monaco-editor/react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Badge, type BadgeKind } from '../../components/Badge';
import { ErrorMessage, Loading } from '../../components/States';
import { errorMessage, ApiError } from '../../services/api';
import { getExercise, getSubmission, listSubmissions, submitCode } from '../../services/lectureApi';
import { FINAL_STATUSES, type Exercise, type Submission } from '../../services/types';
import { usePyodide, type PracticeResult } from './usePyodide';

interface Props {
  exerciseId: string;
  alreadyPassed: boolean;
  onGradingStart: () => void;
  onGradingEnd: (s: Submission) => void;
  onContinue: () => void;
}

const STATUS_LABEL: Record<Submission['status'], [BadgeKind, string]> = {
  queued: ['info', 'Queued'], running: ['info', 'Running'], passed: ['success', 'Passed'],
  failed: ['warning', 'Needs retry'], timeout: ['warning', 'Timed out — needs retry'], error: ['danger', 'Grader unavailable'],
};

export function ExerciseLab({ exerciseId, alreadyPassed, onGradingStart, onGradingEnd, onContinue }: Props) {
  const [exercise, setExercise] = useState<Exercise | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [code, setCode] = useState('');
  const [simpleEditor, setSimpleEditor] = useState(false);
  const [practice, setPractice] = useState<PracticeResult | null>(null);
  const [history, setHistory] = useState<Submission[]>([]);
  const [grading, setGrading] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const keyRef = useRef<string | null>(null);
  const runtime = usePyodide();

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      const [ex, subs] = await Promise.all([getExercise(exerciseId), listSubmissions(exerciseId)]);
      setExercise(ex); setHistory(subs);
      setCode(ex.starter_code);
    } catch (e) {
      setLoadError(errorMessage(e));
    }
  }, [exerciseId]);
  useEffect(() => { void load(); }, [load]);

  const latest = history[history.length - 1];
  const passed = alreadyPassed || latest?.status === 'passed' || history.some((h) => h.status === 'passed');
  const countedAttempts = history.filter((h) => ['passed', 'failed', 'timeout'].includes(h.status)).length;
  const exhausted = exercise?.max_attempts != null && countedAttempts >= exercise.max_attempts && !passed;

  async function runPractice() {
    setPractice(null);
    setPractice(await runtime.run(code));
  }

  async function submit() {
    if (!exercise) return;
    setSubmitError(null); setGrading(true); onGradingStart();
    keyRef.current ??= crypto.randomUUID(); // reused if this exact click is retried after a network error
    try {
      const { submission_id } = await submitCode(exercise.id, code, keyRef.current);
      keyRef.current = null;
      let sub = await getSubmission(submission_id);
      for (let i = 0; i < 90 && !FINAL_STATUSES.includes(sub.status); i++) {
        await new Promise((r) => setTimeout(r, 1000));
        sub = await getSubmission(submission_id);
      }
      if (!FINAL_STATUSES.includes(sub.status)) throw new ApiError(0, 'TIMEOUT', 'Grading is taking longer than expected. Check back in a moment.');
      setHistory(await listSubmissions(exercise.id));
      onGradingEnd(sub);
    } catch (e) {
      setSubmitError(errorMessage(e));
      onGradingEnd({ status: 'error' } as Submission); // not a pass; keeps the lab usable
    } finally {
      setGrading(false);
    }
  }

  if (loadError) return <div className="card"><ErrorMessage message={loadError} /><button className="btn btn-secondary" onClick={() => void load()}>Retry</button></div>;
  if (!exercise) return <Loading label="Loading exercise…" />;

  return (
    <section aria-labelledby="lab-title" className="card lab">
      <h2 id="lab-title">{exercise.title}</h2>
      <p className="instructions">{exercise.instructions}</p>
      <div className="lab-grid">
        <div>
          <label htmlFor="code-editor" className="visually-hidden">Python code</label>
          {simpleEditor ? (
            <textarea id="code-editor" className="simple-editor" value={code} spellCheck={false} onChange={(e) => setCode(e.target.value)} rows={14} />
          ) : (
            <div className="editor-frame" id="code-editor">
              <Editor
                height="320px" language="python" theme="vs-dark" value={code}
                onChange={(v) => setCode(v ?? '')}
                loading={<Loading label="Loading editor…" />}
                options={{ minimap: { enabled: false }, fontSize: 15, tabSize: 4, scrollBeyondLastLine: false, ariaLabel: 'Python code editor' }}
              />
            </div>
          )}
          <p><button className="btn btn-tertiary" onClick={() => setSimpleEditor((v) => !v)}>{simpleEditor ? 'Use code editor' : 'Use simple text editor'}</button></p>
          <div className="actions">
            <button className="btn btn-secondary" onClick={() => void runPractice()} disabled={runtime.status !== 'ready'}>
              {runtime.status === 'running' ? 'Running…' : 'Run practice'}
            </button>
            <button className="btn btn-primary" onClick={() => void submit()} disabled={grading || exhausted || !code.trim()}>
              {grading ? 'Grading…' : 'Submit for grading'}
            </button>
          </div>
          {runtime.status === 'loading' && <Loading label="Loading Python in your browser…" />}
          {runtime.status === 'error' && <div><ErrorMessage message={runtime.loadError ?? 'Runtime error'} /><button className="btn btn-secondary" onClick={() => void runtime.retry()}>Retry loading Python</button></div>}
        </div>
        <div>
          <h3>Practice output <span className="muted">(practice only — not your grade)</span></h3>
          <pre className="output" aria-live="polite">{practice ? (practice.stdout + (practice.error ? `\n${practice.error}` : '') || '(no output)') : 'Run your code to see output here.'}</pre>
          {practice?.truncated && <p className="muted">Output was cut off.</p>}

          <h3>Official result</h3>
          {grading && <Loading label="Grading your submission…" />}
          {!grading && !latest && <p>Not submitted yet.</p>}
          {!grading && latest && (
            <div role="status">
              <Badge kind={STATUS_LABEL[latest.status][0]}>{STATUS_LABEL[latest.status][1]}</Badge>
              {latest.infrastructure_error
                ? <p><strong>This was a problem with the grading system, not your code.</strong> Your attempt was not counted. Please try again.</p>
                : <p>Score: {latest.score ?? 0}% — {latest.passed_tests}/{latest.total_tests} checks passed (pass mark {exercise.pass_threshold}%)</p>}
              <ul>{latest.feedback.map((f, i) => <li key={i}>{f.message}</li>)}</ul>
              {latest.status !== 'passed' && !latest.infrastructure_error && !exhausted && <p>Read the feedback, change your code, and submit again.</p>}
            </div>
          )}
          {submitError && <ErrorMessage message={submitError} />}
          {exhausted && <p role="alert">You have used all {exercise.max_attempts} attempts. Ask your teacher for help.</p>}
          {passed && !grading && <button className="btn btn-primary" onClick={onContinue}>Continue to exit check</button>}
        </div>
      </div>
      {history.length > 0 && (
        <details>
          <summary>Attempt history ({history.length}{exercise.max_attempts ? ` of ${exercise.max_attempts} max` : ''})</summary>
          <ol>{history.map((h) => <li key={h.submission_id}>Attempt {h.submission_number}: {STATUS_LABEL[h.status][1]}{h.score != null ? ` (${h.score}%)` : ''}</li>)}</ol>
        </details>
      )}
    </section>
  );
}
