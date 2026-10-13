import { useState } from 'react';
import type { CheckpointResult, Segment } from '../services/types';
import { Badge } from './Badge';

interface Props {
  segment: Segment;
  result?: CheckpointResult;
  submitting: boolean;
  isExitCheck: boolean;
  onSubmit: (optionId: string) => void;
  onContinue: () => void;
  onRetry: () => void;
}

export function McqCheckpoint({ segment, result, submitting, isExitCheck, onSubmit, onContinue, onRetry }: Props) {
  const [selected, setSelected] = useState<string | null>(null);
  const cp = segment.checkpoint;
  if (!cp) return <p role="alert">This checkpoint is not configured.</p>;
  const { question } = cp;

  if (result) {
    return (
      <section aria-labelledby="mcq-title" className="card">
        <p className="muted">{isExitCheck ? 'Exit check' : 'Knowledge check'}</p>
        <h2 id="mcq-title">{segment.title}</h2>
        <p className="prompt">{question.prompt}</p>
        <div role="status" className={`result ${result.is_correct ? 'result-correct' : 'result-wrong'}`}>
          <Badge kind={result.is_correct ? 'success' : 'warning'}>{result.is_correct ? 'Correct' : 'Not quite'}</Badge>
          <p style={{ marginTop: 8 }}>Score: {result.score}</p>
          <p style={{ margin: 0 }}>{result.explanation}</p>
        </div>
        {result.checkpoint_completed ? (
          <button className="btn btn-primary" onClick={onContinue}>{isExitCheck ? 'Finish lecture' : 'Continue lesson'}</button>
        ) : (
          <>
            <p className="muted">This check needs a correct answer before you can finish. Review the explanation, then try again.</p>
            <button className="btn btn-primary" onClick={() => { setSelected(null); onRetry(); }}>Try again</button>
          </>
        )}
      </section>
    );
  }

  return (
    <form
      className="card"
      aria-labelledby="mcq-title"
      onSubmit={(e) => { e.preventDefault(); if (selected && !submitting) onSubmit(selected); }}
    >
      <p className="muted">{isExitCheck ? 'Exit check' : 'Knowledge check — the video is paused'}</p>
      <h2 id="mcq-title">{segment.title}</h2>
      <fieldset disabled={submitting}>
        <legend className="prompt">{question.prompt}</legend>
        {question.options.map((o) => (
          <label key={o.id} className="option">
            <input type="radio" name={`q-${question.id}`} value={o.id} checked={selected === o.id} onChange={() => setSelected(o.id)} />
            <span>{o.text}</span>
          </label>
        ))}
      </fieldset>
      <button className="btn btn-primary" type="submit" disabled={!selected || submitting}>{submitting ? 'Checking…' : 'Submit answer'}</button>
    </form>
  );
}
