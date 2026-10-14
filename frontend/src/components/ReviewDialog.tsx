import { useEffect, useRef } from 'react';
import type { Segment } from '../services/types';

/** Replay a lecture section from inside the lab (remediation, §10). Read-only: it never changes progress. */
export function ReviewDialog({ segment, onClose }: { segment: Segment | null; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (segment && !d.open) {
      if (d.showModal) d.showModal();
      else d.setAttribute('open', '');
    }
    if (!segment && d.open) {
      if (d.close) d.close();
      else d.removeAttribute('open');
    }
  }, [segment]);
  return (
    <dialog ref={ref} className="dialog dialog-wide" aria-labelledby="review-title" onCancel={(e) => { e.preventDefault(); onClose(); }}>
      {segment && (
        <>
          <h2 id="review-title">Review: {segment.title}</h2>
          {segment.media?.url ? (
            <div className="video-frame"><video src={segment.media.url} controls playsInline preload="metadata" aria-label={segment.title} /></div>
          ) : segment.body ? <p>{segment.body}</p> : <p className="muted">This section has no replayable content.</p>}
          {segment.media?.transcript && <details><summary>Transcript</summary><p>{segment.media.transcript}</p></details>}
          <p className="muted">Replaying a section doesn't change your progress. Close this when you're ready to try again.</p>
          <div className="actions"><button className="btn btn-primary" onClick={onClose} autoFocus>Back to the exercise</button></div>
        </>
      )}
    </dialog>
  );
}
