import { Suspense, lazy, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Badge } from '../components/Badge';
import { Icon } from '../components/Icon';
import { ErrorMessage, Loading } from '../components/States';
import { STATUS_LABEL } from '../components/SubmissionStatus';
import { ApiError, errorMessage } from '../services/api';
import { getExercise, listSubmissions, submitAnswers } from '../services/lectureApi';
import type { Exercise, Submission } from '../services/types';

const ExerciseLab = lazy(() => import('../features/lab/ExerciseLab').then((m) => ({ default: m.ExerciseLab })));

/** One practical lab, opened from the Practical Labs section. The kind decides the experience; the server decides the result. */
export function LabPage() {
  const { exerciseId = '' } = useParams();
  const q = useQuery({ queryKey: ['lab', exerciseId], queryFn: () => getExercise(exerciseId) });
  if (q.isPending) return <main className="page"><Loading label="Loading the lab…" /></main>;
  if (q.isError) {
    const e = q.error;
    const locked = e instanceof ApiError && e.status === 400;
    const checks = locked && e.code === 'CHECKPOINT_REQUIRED';
    const missing = e instanceof ApiError && e.status === 404;
    return (
      <main className="page">
        <ErrorMessage message={checks ? 'This lab opens after the knowledge checks in its lecture: open the lecture from your dashboard and continue to the lab.' : locked ? 'This lab is locked: complete the earlier lecture first.' : missing ? 'This lab was not found or is not published.' : errorMessage(e)} onRetry={locked || missing ? undefined : () => void q.refetch()} />
        <Link to="/labs">Back to practical labs</Link>
      </main>
    );
  }
  const ex = q.data;
  return (
    <main className="page">
      <nav className="crumbs" aria-label="Breadcrumb"><Link to="/labs">Practical labs</Link> <span aria-hidden="true">›</span> <span aria-current="page">Lecture {ex.lecture?.lecture_number ?? ''}: {ex.title}</span></nav>
      <h1>{ex.title}</h1>
      {ex.lecture?.title && <p className="muted">Lecture {ex.lecture.lecture_number}: {ex.lecture.title} · <Link to={`/lectures/${ex.lecture.id}`}>open the lecture</Link></p>}
      {ex.lab_kind === 'code' && (
        <Suspense fallback={<Loading label="Loading the coding lab…" />}>
          <ExerciseLab key={ex.id} exerciseId={ex.id} sections={[]} alreadyPassed={false} mode="lab" onGradingStart={() => undefined} onGradingEnd={() => undefined} onContinue={() => undefined} />
        </Suspense>
      )}
      {ex.lab_kind === 'quiz' && <QuizLab ex={ex} />}
      {(ex.lab_kind === 'written' || ex.lab_kind === 'upload') && <ReviewedLab ex={ex} />}
    </main>
  );
}

function useHistory(exerciseId: string) {
  return useQuery({ queryKey: ['lab-history', exerciseId], queryFn: () => listSubmissions(exerciseId) });
}

function LastResult({ sub }: { sub: Submission }) {
  const [kind, label] = STATUS_LABEL[sub.status];
  return <p><Badge kind={kind}>{label}</Badge>{sub.review && <> <span className="muted">— {sub.review.feedback}</span></>}</p>;
}

/** Question set: answers are marked on the server in one go; pass = every question right. */
function QuizLab({ ex }: { ex: Exercise }) {
  const qc = useQueryClient();
  const history = useHistory(ex.id);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [outcome, setOutcome] = useState<Submission | null>(null);
  const [error, setError] = useState('');
  const submit = useMutation({
    mutationFn: async () => {
      const r = await submitAnswers(ex.id, crypto.randomUUID(), { answers }, ex.content_version);
      const { getSubmission } = await import('../services/lectureApi');
      return getSubmission(r.submission_id);
    },
    onSuccess: (s) => { setOutcome(s); setError(''); void qc.invalidateQueries({ queryKey: ['lab-history', ex.id] }); void qc.invalidateQueries({ queryKey: ['labs'] }); },
    onError: (e) => setError(errorMessage(e)),
  });
  const last = outcome ?? history.data?.submissions.at(-1) ?? null;
  const passed = history.data?.submissions.some((s) => s.status === 'passed') ?? false;
  const complete = ex.questions.every((qq) => answers[qq.id]);
  return (
    <section className="card" aria-labelledby="quiz-h">
      <h2 id="quiz-h">{passed ? 'Passed' : 'Question set'}</h2>
      <p>{ex.instructions}</p>
      <p className="muted">Answer every question, then save. You pass when every answer is correct. You can try again as often as you need.</p>
      {last && <LastResult sub={last} />}
      <form onSubmit={(e) => { e.preventDefault(); submit.mutate(); }}>
        {ex.questions.map((qq) => {
          const res = outcome?.quiz_results?.find((r) => r.question_id === qq.id);
          return (
            <fieldset key={qq.id} className="quiz-question">
              <legend>{qq.question_order}. {qq.prompt}</legend>
              {qq.options.map((o) => (
                <label key={o.id}><input type="radio" name={`q-${qq.id}`} value={o.id} checked={answers[qq.id] === o.id} onChange={() => setAnswers({ ...answers, [qq.id]: o.id })} /> <span>{o.text}</span></label>
              ))}
              {res && <p className={res.correct ? 'quiz-result-ok' : 'quiz-result-bad'} role="status">{res.correct ? '✓ Correct.' : '✕ Not correct.'} {res.explanation}</p>}
            </fieldset>
          );
        })}
        {error && <p role="alert" className="field-error">{error}</p>}
        <div className="actions"><button className="btn btn-primary" type="submit" disabled={!complete || submit.isPending}>{submit.isPending ? 'Checking…' : 'Save & check'}</button></div>
      </form>
    </section>
  );
}

/** Written and upload labs: the learner submits; a teacher marks against the rubric. */
function ReviewedLab({ ex }: { ex: Exercise }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const history = useHistory(ex.id);
  const [text, setText] = useState('');
  const [link, setLink] = useState('');
  const [notes, setNotes] = useState('');
  const [ticks, setTicks] = useState<boolean[]>(ex.checklist.map(() => false));
  const [error, setError] = useState('');
  const submit = useMutation({
    mutationFn: () => submitAnswers(ex.id, crypto.randomUUID(), ex.lab_kind === 'written' ? { source_code: text } : { source_code: notes, answers: { link, notes, checklist: ticks } }, ex.content_version),
    onSuccess: () => { setError(''); void qc.invalidateQueries({ queryKey: ['lab-history', ex.id] }); void qc.invalidateQueries({ queryKey: ['labs'] }); void qc.invalidateQueries({ queryKey: ['lab', ex.id] }); },
    onError: (e) => setError(errorMessage(e)),
  });
  const last = history.data?.submissions.at(-1) ?? null;
  const waiting = last?.status === 'submitted';
  const passed = history.data?.submissions.some((s) => s.status === 'passed') ?? false;
  return (
    <section className="card" aria-labelledby="task-h">
      <h2 id="task-h">{ex.lab_kind === 'written' ? 'Written task' : 'Project upload'}</h2>
      <h3>Objective</h3><p>{ex.objective}</p>
      <h3>Task</h3><p className="instructions">{ex.instructions}</p>
      {ex.constraints && <><h3>Constraints</h3><p>{ex.constraints}</p></>}
      {ex.rubric.length > 0 && (
        <><h3>How your teacher will mark it</h3>
          <ul>{ex.rubric.map((r) => <li key={r.criterion}><strong>{r.criterion}</strong> ({r.max_points} pt{r.max_points === 1 ? '' : 's'}) — {r.description}</li>)}</ul></>
      )}
      {last && <><h3>Latest attempt</h3><LastResult sub={last} /></>}
      {ex.review && !waiting && (
        <div className={`notice ${ex.review.passed ? 'notice-success' : 'notice-warning'}`} role="status">
          <strong>Teacher's decision: {ex.review.passed ? 'passed' : 'not yet'}.</strong> {ex.review.feedback}
          {ex.review.scores.length > 0 && <ul style={{ margin: '4px 0 0' }}>{ex.review.scores.map((s) => <li key={s.criterion}>{s.criterion}: {s.points}{s.max_points != null ? ` / ${s.max_points}` : ''}</li>)}</ul>}
        </div>
      )}
      {waiting ? <p role="status" className="notice notice-info">Sent to your teacher. You will see the outcome here.</p> : passed ? <p role="status">You have passed this lab.</p> : (
        <form onSubmit={(e) => { e.preventDefault(); submit.mutate(); }} aria-label={ex.lab_kind === 'written' ? 'Written answer' : 'Project submission'}>
          {ex.lab_kind === 'written' ? (
            <>
              <label htmlFor="written-answer">Your answer</label>
              <textarea id="written-answer" rows={12} maxLength={8000} value={text} onChange={(e) => setText(e.target.value)} required />
              <p className="field-hint">{text.length} / 8000 characters</p>
            </>
          ) : (
            <>
              <fieldset style={{ border: 0, padding: 0 }}>
                <legend>Checklist (all items must be done)</legend>
                {ex.checklist.map((item, i) => <label key={item} style={{ display: 'block' }}><input type="checkbox" checked={ticks[i]} onChange={(e) => setTicks(ticks.map((t, j) => (j === i ? e.target.checked : t)))} /> {item}</label>)}
              </fieldset>
              <label htmlFor="upload-link">Link to your work (https)</label>
              <input id="upload-link" type="url" required pattern="https://.*" value={link} onChange={(e) => setLink(e.target.value)} placeholder="https://github.com/you/project" />
              <label htmlFor="upload-notes">Notes for your teacher</label>
              <textarea id="upload-notes" rows={5} maxLength={8000} value={notes} onChange={(e) => setNotes(e.target.value)} />
            </>
          )}
          {error && <p role="alert" className="field-error">{error}</p>}
          <div className="actions">
            <button className="btn btn-primary" type="submit" disabled={submit.isPending}><Icon name="flag" size={16} /> {submit.isPending ? 'Sending…' : 'Save & send for review'}</button>
            <button className="btn btn-tertiary" type="button" onClick={() => navigate('/labs')}>Back to labs</button>
          </div>
        </form>
      )}
    </section>
  );
}
