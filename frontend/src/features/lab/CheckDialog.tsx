import { useEffect, useRef } from 'react';
import { Icon } from '../../components/Icon';
import { Loading } from '../../components/States';
import type { Submission } from '../../services/types';
import type { QuickCheckResult } from './usePyodide';

export type CheckPhase = 'quick' | 'official' | 'official-pending' | 'failed-to-send';
export interface CheckOutcome {
  phase: CheckPhase;
  quick: QuickCheckResult | null;     // instant browser result (visible checks only), if available
  official: Submission | null;        // server result when it has arrived
  sendError?: string | null;
}

interface Props {
  open: boolean;
  outcome: CheckOutcome | null;
  hintsLeft: number;
  redoAvailable: boolean;
  showFix: boolean;          // the free error guidance has been requested
  onDismiss: () => void;
  onShowHint: () => void;    // the fix for this error (free)
  onBulbHint: () => void;    // one of the 3 lab hints
  onRedo: () => void;
  onContinue?: () => void;
}

function failedLines(outcome: CheckOutcome): string[] {
  const lines: string[] = [];
  const err = outcome.official?.feedback.find((f) => f.message.startsWith('Your program raised'))?.message
    ?? (outcome.quick?.error ? `Your program raised ${outcome.quick.error.type}${outcome.quick.error.line ? ` on line ${outcome.quick.error.line}` : ''}: ${outcome.quick.error.message}` : null);
  if (err) lines.push(err);
  const criteria = outcome.official?.criteria ?? outcome.quick?.criteria ?? [];
  for (const c of criteria) if (!c.passed) lines.push(`Not passed: ${c.label}`);
  if (outcome.official && ['timeout', 'error', 'expired'].includes(outcome.official.status)) lines.push(outcome.official.feedback[0]?.message ?? '');
  return lines.filter(Boolean);
}

/** The Save & check popup: instant browser verdict first, then the official server verdict replaces it. */
export function CheckDialog({ open, outcome, showFix, hintsLeft, redoAvailable, onDismiss, onShowHint, onBulbHint, onRedo, onContinue }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) { if (d.showModal) d.showModal(); else d.setAttribute('open', ''); }
    if (!open && d.open) { if (d.close) d.close(); else d.removeAttribute('open'); }
  }, [open]);
  const official = outcome?.official ?? null;
  const officialFinal = !!official && !['queued', 'running'].includes(official.status);
  const passed = officialFinal && official.status === 'passed';
  const quickPassed = outcome?.quick?.status === 'passed';
  const fault = officialFinal && ['error', 'expired', 'cancelled'].includes(official.status);
  const title = passed ? 'Lab passed' : officialFinal ? (fault ? 'The checker had a problem' : 'Not quite right yet') : outcome?.quick?.status === 'failed' || outcome?.quick?.status === 'timeout' ? 'Not quite right yet' : outcome?.phase === 'failed-to-send' ? 'Could not send your work' : 'Checking your work';
  const lines = outcome ? failedLines(outcome) : [];
  const remediation = official?.remediation ?? [];
  return (
    <dialog ref={ref} className="dialog check-dialog" aria-labelledby="check-title" onCancel={(e) => { e.preventDefault(); onDismiss(); }} data-testid="check-dialog">
      <h2 id="check-title">{title}</h2>
      {outcome?.phase === 'failed-to-send' && <p role="alert">{outcome.sendError}</p>}
      {!officialFinal && outcome?.phase !== 'failed-to-send' && (
        <div>
          {quickPassed && <p className="notice notice-success" role="status">Looks right in the browser — confirming officially…</p>}
          {!quickPassed && lines.length > 0 && <ul className="check-errors">{lines.map((l) => <li key={l}>{l}</li>)}</ul>}
          <Loading label={outcome?.quick ? 'Official check running on the server…' : 'Sending your work to the official checker…'} />
        </div>
      )}
      {officialFinal && !passed && !fault && (
        <div role="status">
          <ul className="check-errors">{lines.map((l) => <li key={l}>{l}</li>)}</ul>
          {showFix && remediation.length > 0 && (
            <div className="notice notice-info" data-testid="check-fix">
              <strong>How to fix it</strong>
              <ul style={{ margin: '4px 0 0', paddingLeft: 18 }}>{remediation.map((r, i) => <li key={i}>{r.objective ? <span className="muted">{r.objective}: </span> : null}{r.text}</li>)}</ul>
            </div>
          )}
          {!showFix && remediation.length > 0 && <p className="muted">“Show hint” explains how to fix each of these.</p>}
          {showFix && remediation.length === 0 && <p className="muted">Read the error above: it names the line to look at.</p>}
        </div>
      )}
      {officialFinal && fault && <p role="status">{official.feedback[0]?.message ?? 'Please try again.'}</p>}
      {passed && <p role="status">All checks passed. Your result is recorded.</p>}
      <div className="actions">
        {passed ? (
          <>
            {onContinue && <button className="btn btn-primary" onClick={onContinue} autoFocus>Continue</button>}
            <button className="btn btn-secondary" onClick={onDismiss} autoFocus={!onContinue}>Close</button>
          </>
        ) : (
          <>
            <button className="btn btn-secondary" onClick={onDismiss} autoFocus>Dismiss</button>
            {officialFinal && !fault && !showFix && <button className="btn btn-primary" onClick={onShowHint}>Show hint</button>}
            {officialFinal && !fault && showFix && hintsLeft > 0 && <button className="btn btn-primary" onClick={onBulbHint}><Icon name="bulb" size={16} /> Lab hint ({hintsLeft} left)</button>}
            {officialFinal && !fault && redoAvailable && <button className="btn btn-tertiary" onClick={onRedo}><Icon name="reset" size={16} /> Redo the lab</button>}
          </>
        )}
      </div>
    </dialog>
  );
}
