import { useEffect, useRef, useState } from 'react';
import type { Segment } from '../services/types';

interface Props {
  segment: Segment;
  startAt: number;
  onPlay: () => void;
  onPause: () => void;
  onEnded: () => void;
  onError: () => void;
  onPosition: (seconds: number) => void;
}

/** HTML5 video: reliable `ended` events. Provides explicit fallbacks when autoplay/media fail. */
export function VideoSegment({ segment, startAt, onPlay, onPause, onEnded, onError, onPosition }: Props) {
  const ref = useRef<HTMLVideoElement>(null);
  const lastSaved = useRef(0);
  const [autoplayBlocked, setAutoplayBlocked] = useState(false);
  const url = segment.media?.url;

  useEffect(() => {
    const v = ref.current;
    if (!v || !url) return;
    v.play().catch(() => setAutoplayBlocked(true)); // autoplay may be blocked: show a Play button
  }, [url, segment.id]);

  if (!url) return <p role="alert">This video has no media configured.</p>;

  return (
    <section aria-labelledby="video-title" className="card">
      <h2 id="video-title">{segment.title}</h2>
      <div className="video-frame">
        <video
          ref={ref}
          key={segment.id}
          src={url}
          controls
          preload="auto"
          playsInline
          onLoadedMetadata={(e) => { if (startAt > 0 && startAt < e.currentTarget.duration) e.currentTarget.currentTime = startAt; }}
          onPlay={() => { setAutoplayBlocked(false); onPlay(); }}
          onPause={() => { if (!ref.current?.ended) onPause(); }}
          onEnded={onEnded}
          onError={onError}
          onTimeUpdate={(e) => {
            const t = e.currentTarget.currentTime;
            if (Math.abs(t - lastSaved.current) >= 10) { lastSaved.current = t; onPosition(t); }
          }}
        >
          <track kind="captions" />
        </video>
      </div>
      {autoplayBlocked && (
        <p>
          Your browser blocked automatic playback.{' '}
          <button className="btn btn-secondary" onClick={() => ref.current?.play().catch(() => onError())}>Play video</button>
        </p>
      )}
      <p className="muted">
        Video not advancing?{' '}
        <button className="btn btn-tertiary" onClick={onEnded}>I've finished this video — continue</button>
      </p>
    </section>
  );
}
