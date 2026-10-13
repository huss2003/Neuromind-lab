import Editor from '@monaco-editor/react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Badge, type BadgeKind } from '../../components/Badge';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { Icon } from '../../components/Icon';
import { ErrorMessage, Loading } from '../../components/States';
import { ApiError, errorMessage } from '../../services/api';
import { getExercise, getSubmission, listSubmissions, revealHint, saveDraft, submitCode } from '../../services/lectureApi';
import { FINAL_STATUSES, type Exercise, type Submission } from '../../services/types';
import { usePyodide, type PracticeResult } from './usePyodide';

interface Props {
  exerciseId: string;
  alreadyPassed: boolean;
  onGradingStart: () => void;
  onGradingEnd: (s: Submission) => void;
  onContinue: () => void;
}

type Tab = 'task' | 'code' | 'output' | 'result';
type SaveState = 'saved' | 'saving' | 'unsaved' | 'error';

export const STATUS_LABEL: Record<Submission['status'], [BadgeKind, string]> = {
  queued: ['info', 'Queued'], running: ['info', 'Running'], passed: ['success', 'Passed'],
  failed: ['warning', 'Needs retry'], timeout: ['warning', 'Timed out — needs retry'], error: ['danger', 'Grader unavailable'],
};
const AUTOSAVE_MS = 1500;

export function ExerciseLab({ exerciseId, alreadyPassed, onGradingStart, onGradingEnd, onContinue }: Props) {
  const [exercise, setExercise] = useState<Exercise | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [code, setCode] = useState('');
  const [savedCode, setSavedCode] = useState('');
  const [saveState, setSaveState] = useState<SaveState>('saved');
  const [simpleEditor, setSimpleEditor] = useState(false);
  const [tab, setTab] = useState<Tab>('code');
  const [practice, setPractice] = useState<PracticeResult | null>(null);
  const [history, setHistory] = useState<Submission[]>([]);
  const [bestScore, setBestScore] = useState<number | null>(null);
  const [live, setLive] = useState<Submission | null>(null);
  const [grading, setGrading] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [hintBusy, setHintBusy] = useState(false);
  const [hintError, setHintError] = useState<string | null>(null);
  const [resetOpen, setResetOpen] = useState(false);
  const keyRef = useRef<string | null>(null);
  const codeRef = useRef('');
  const runtime = usePyodide();
  codeRef.current = code;

  const load = useCallback(async (initial: boolean) => {
    setLoadError(null);
    try {
      const [ex, subs] = await Promise.all([getExercise(exerciseId), listSubmissions(exerciseId)]);
      setExercise(ex);
      setHistory(subs.submissions);
      setBestScore(subs.best_score);
      if (initial) {
        const start = ex.draft ?? ex.starter_code;
        setCode(start);
        setSavedCode(start);
      }
    } catch (e) {
      setLoadError(errorMessage(e));
    }
  }, [exerciseId]);
  useEffect(() => { void load(true); }, [load]);

  const persistDraft = useCallback(async (value: string) => {
    setSaveState('saving');
    try {
      await saveDraft(exerciseId, value);
      setSavedCode(value);
      setSaveState(codeRef.current === value ? 'saved' : 'unsaved');
    } catch {
      setSaveState('error');
    }
  }, [exerciseId]);

  // Debounced autosave of work in progress (server-side, so it survives refresh and device changes).
  useEffect(() => {
    if (!exercise || !exercise.unlocked || code === savedCode) return;
    setSaveState((s) => (s === 'saving' ? s : 'unsaved'));
    const t = setTimeout(() => { void persistDraft(code); }, AUTOSAVE_MS);
    return () => clearTimeout(t);
  }, [code, savedCode, exercise, persistDraft]);

  // Warn before leaving with unsaved work (§7.1).
  const dirty = !!exercise && (code !== savedCode || saveState === 'error');
  useEffect(() => {
    if (!dirty) return;
    const warn = (e: BeforeUnloadEvent) => { e.preventDefault(); e.returnValue = ''; };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty]);

  const latest = live ?? history[history.length - 1];
  const passed = alreadyPassed || history.some((h) => h.status === 'passed');
  const exhausted = exercise?.max_attempts != null && history.filter((h) => ['passed', 'failed', 'timeout'].includes(h.status)).length >= exercise.max_attempts && !passed;

  async function runPractice() {
    setPractice(null);
    setTab('output');
    setPractice(await runtime.run(code));
  }

  async function submit() {
    if (!exercise || grading) return;
    setSubmitError(null); setGrading(true); setLive(null); setTab('result'); onGradingStart();
    keyRef.current ??= crypto.randomUUID(); // reused if this exact click is retried after a network error
    let outcome: Submission | null = null;
    try {
      const { submission_id } = await submitCode(exercise.id, code, keyRef.current);
      keyRef.current = null;
      let sub = await getSubmission(submission_id);
      setLive(sub);
      for (let i = 0; i < 90 && !FINAL_STATUSES.includes(sub.status); i++) {
        await new Promise((r) => setTimeout(r, 1000));
        sub = await getSubmission(submission_id);
        setLive(sub);
      }
      if (!FINAL_STATUSES.includes(sub.status)) throw new ApiError(0, 'TIMEOUT', 'Grading is taking longer than expected. Your submission is saved — check back in a moment.');
      outcome = sub;
      if (sub.status !== 'error') void persistDraft(code);
      await load(false); // refresh history, best score and (reset) hints for the next attempt
      setLive(null);
    } catch (e) {
      setSubmitError(errorMessage(e));
    } finally {
      setGrading(false);
      onGradingEnd(outcome ?? ({ status: 'error' } as Submission)); // never a pass unless the server said so
    }
  }

  async function showHint() {
    if (!exercise) return;
    setHintBusy(true); setHintError(null);
    try {
      const h = await revealHint(exercise.id, exercise.hints_revealed.length);
      setExercise({ ...exercise, hints_revealed: [...exercise.hints_revealed, h.text] });
    } catch (e) {
      setHintError(errorMessage(e));
    } finally {
      setHintBusy(false);
    }
  }

  function confirmReset() {
    if (!exercise) return;
    setCode(exercise.starter_code);
    setPractice(null);
    setResetOpen(false);
  }

  if (loadError) return <div className="card"><ErrorMessage message={loadError} onRetry={() => void load(true)} /></div>;
  if (!exercise) return <Loading label="Loading exercise…" />;
  if (!exercise.unlocked) return <div className="card"><h2>{exercise.title}</h2><p role="status">This exercise unlocks after you complete the earlier knowledge checks.</p></div>;

  const nextHint = exercise.hints_revealed.length;
  const tabs: [Tab, string][] = [['task', 'Task'], ['code', 'Code'], ['output', 'Output'], ['result', 'Result']];
  const saveText = { saved: 'All changes saved', saving: 'Saving…', unsaved: 'Unsaved changes', error: 'Could not save — check your connection' }[saveState];

  return (
    <section aria-labelledby="lab-title" className="card lab">
      <div className="row">
        <div>
          <p className="muted" style={{ margin: 0 }}>Practical lab</p>
          <h2 id="lab-title" style={{ marginBottom: 4 }}>{exercise.title}</h2>
        </div>
        <div>
          {bestScore != null ? <Badge kind={bestScore >= exercise.pass_threshold ? 'success' : 'info'}>{`Best score ${bestScore}% · pass mark ${exercise.pass_threshold}%`}</Badge> : <Badge kind="neutral">{`Pass mark ${exercise.pass_threshold}%`}</Badge>}
        </div>
      </div>

      <div className="lab-tabs" role="tablist" aria-label="Lab sections">
        {tabs.map(([id, label]) => (
          <button key={id} role="tab" id={`tab-${id}`} aria-selected={tab === id} aria-controls={`pane-${id}`} onClick={() => setTab(id)}>{label}</button>
        ))}
      </div>

      <div className="lab-grid">
        <div>
          <div className="lab-pane" id="pane-task" role="tabpanel" aria-labelledby="tab-task" hidden={tab !== 'task'}>
            <h3>Instructions</h3>
            <p className="instructions">{exercise.instructions}</p>
            {exercise.hints_total > 0 && (
              <div>
                {exercise.hints_revealed.map((h, i) => <p key={i} className="hint"><Icon name="bulb" size={16} /> <strong>Hint {i + 1}:</strong> {h}</p>)}
                {nextHint < exercise.hints_total && (
                  <button className="btn btn-tertiary" onClick={() => void showHint()} disabled={hintBusy}>
                    <Icon name="bulb" size={16} /> Show hint {nextHint + 1} of {exercise.hints_total}
                  </button>
                )}
                <p className="muted">Each hint lowers <em>this attempt's</em> score by {exercise.hint_penalty_percent} points. It never lowers a score you have already earned.</p>
                {hintError && <p role="alert" className="field-error">{hintError}</p>}
              </div>
            )}
          </div>

          <div className="lab-pane" id="pane-code" role="tabpanel" aria-labelledby="tab-code" hidden={tab !== 'code'}>
            <h3 className="visually-hidden">Code</h3>
            <label htmlFor="code-editor" className="visually-hidden">Python code</label>
            {simpleEditor ? (
              <textarea id="code-editor" className="simple-editor" value={code} spellCheck={false} onChange={(e) => setCode(e.target.value)} rows={14} />
            ) : (
              <div className="editor-frame" id="code-editor">
                <Editor
                  height="340px" language="python" theme="vs-dark" value={code}
                  onChange={(v) => setCode(v ?? '')}
                  loading={<Loading label="Loading editor…" />}
                  options={{ minimap: { enabled: false }, fontSize: 15, tabSize: 4, scrollBeyondLastLine: false, lineNumbers: 'on', ariaLabel: 'Python code editor', accessibilitySupport: 'auto' }}
                />
              </div>
            )}
            <div className="statusbar">
              <span role="status">{saveText}</span>
              <span>
                <button className="btn btn-tertiary" onClick={() => setSimpleEditor((v) => !v)}>{simpleEditor ? 'Use code editor' : 'Use simple text editor'}</button>
                <button className="btn btn-tertiary" onClick={() => setResetOpen(true)}><Icon name="reset" size={16} /> Reset to starter</button>
              </span>
            </div>
            <div className="actions">
              <button className="btn btn-secondary" onClick={() => void runPractice()} disabled={runtime.status !== 'ready'}>
                <Icon name="play" size={16} /> {runtime.status === 'running' ? 'Running…' : 'Run practice'}
              </button>
              <button className="btn btn-primary" onClick={() => void submit()} disabled={grading || exhausted || !code.trim()}>
                <Icon name="flag" size={16} /> {grading ? 'Grading…' : 'Submit for grading'}
              </button>
            </div>
            <p className="muted">Practice runs happen in your browser and don't count. Submitting sends your code to the official grader.</p>
            {runtime.status === 'loading' && <Loading label="Loading Python in your browser… (first run takes a few seconds)" />}
            {runtime.status === 'error' && (
              <div>
                <ErrorMessage message={runtime.loadError ?? 'The practice runtime failed to start.'} onRetry={() => void runtime.retry()} />
              </div>
            )}
          </div>
        </div>

        <div>
          <div className="lab-pane" id="pane-output" role="tabpanel" aria-labelledby="tab-output" hidden={tab !== 'output'}>
            <h3>Practice output <span className="muted">(not your grade)</span></h3>
            {!practice && <pre className="output" aria-live="polite">Run your code to see its output here.</pre>}
            {practice && (
              <div aria-live="polite">
                <p className="muted" style={{ margin: '0 0 4px' }}>Output</p>
                <pre className="output">{practice.stdout || '(no output)'}</pre>
                {(practice.error || practice.stderr) && (
                  <>
                    <p className="muted" style={{ margin: '8px 0 4px' }}>Errors{practice.errorLine ? ` — line ${practice.errorLine}` : ''}</p>
                    <pre className="output stderr">{[practice.stderr, practice.error].filter(Boolean).join('\n')}</pre>
                  </>
                )}
                {practice.truncated && <p className="muted">Output was cut off at the limit.</p>}
              </div>
            )}
          </div>

          <div className="lab-pane" id="pane-result" role="tabpanel" aria-labelledby="tab-result" hidden={tab !== 'result'}>
            <h3>Official result</h3>
            {grading && !live && <Loading label="Sending your code to the grader…" />}
            {grading && live && <Loading label={live.status === 'queued' ? 'Waiting in the grading queue…' : 'Grading your submission…'} />}
            {!grading && !latest && <p>Not submitted yet. When you're ready, choose “Submit for grading”.</p>}
            {!grading && latest && <ResultPanel sub={latest} passMark={exercise.pass_threshold} />}
            {submitError && <ErrorMessage message={submitError} />}
            {exhausted && <p role="alert">You have used all {exercise.max_attempts} attempts. Ask your teacher for help.</p>}
            {passed && !grading && <button className="btn btn-primary" onClick={onContinue}>Continue to exit check</button>}
            {history.length > 0 && (
              <details>
                <summary>Attempt history ({history.length})</summary>
                <div className="table-wrap">
                  <table>
                    <thead><tr><th scope="col">#</th><th scope="col">Result</th><th scope="col">Score</th></tr></thead>
                    <tbody>
                      {history.map((h) => (
                        <tr key={h.submission_id}>
                          <td>{h.submission_number}</td>
                          <td>{STATUS_LABEL[h.status][1]}</td>
                          <td>{h.score != null ? `${h.score}%${h.hints_used ? ` (${h.hints_used} hint${h.hints_used > 1 ? 's' : ''})` : ''}` : '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            )}
          </div>
        </div>
      </div>

      <ConfirmDialog open={resetOpen} title="Reset to starter code?" confirmLabel="Reset code" destructive onConfirm={confirmReset} onCancel={() => setResetOpen(false)}>
        <p>This replaces what you've written with the starter code. Your past submissions are kept.</p>
      </ConfirmDialog>
    </section>
  );
}

export function ResultPanel({ sub, passMark }: { sub: Submission; passMark: number }) {
  const [kind, label] = STATUS_LABEL[sub.status];
  return (
    <div role="status">
      <Badge kind={kind}>{label}</Badge>
      {sub.infrastructure_error ? (
        <p><strong>This was a problem with the grading system, not your code.</strong> This attempt was not judged. Please try again.</p>
      ) : (
        <>
          <p style={{ marginTop: 8 }}>
            <strong>Score: {sub.score ?? 0}%</strong> (pass mark {passMark}%) — {sub.passed_tests}/{sub.total_tests} checks passed
            {sub.hints_used ? <><br /><span className="muted">Raw score {sub.raw_score}% − {sub.hint_penalty} points for {sub.hints_used} hint{sub.hints_used > 1 ? 's' : ''}. Your best earlier score is unchanged.</span></> : null}
          </p>
          {sub.criteria && sub.criteria.length > 0 && (
            <ul className="criteria" aria-label="Checks">
              {sub.criteria.map((c, i) => (
                <li key={i}><span aria-hidden="true">{c.passed ? '✓' : '✕'}</span><span><span className="visually-hidden">{c.passed ? 'Passed: ' : 'Not passed: '}</span>{c.label}</span></li>
              ))}
            </ul>
          )}
          {sub.remediation && sub.remediation.length > 0 && (
            <div className="notice notice-info">
              <strong>How to fix it</strong>
              <ul style={{ margin: '4px 0 0', paddingLeft: 18 }}>{sub.remediation.map((r, i) => <li key={i}>{r.text}</li>)}</ul>
              <p>Update your code and submit again — you can retry as often as you need.</p>
            </div>
          )}
          <ul>{sub.feedback.map((f, i) => <li key={i}>{f.message}</li>)}</ul>
        </>
      )}
    </div>
  );
}
