import { useCallback, useEffect, useRef, useState } from 'react';

export type RuntimeStatus = 'idle' | 'loading' | 'ready' | 'running' | 'error';
export interface PracticeResult { stdout: string; stderr: string; error: string | null; errorLine: number | null; truncated: boolean; timedOut: boolean }

const LOAD_TIMEOUT_MS = 60_000;
export const RUN_TIMEOUT_MS = 5_000;

/** Owns a terminable Pyodide worker. A timed-out run terminates the worker and a fresh one loads on demand. */
export function usePyodide() {
  const worker = useRef<Worker | null>(null);
  const seq = useRef(0);
  const [status, setStatus] = useState<RuntimeStatus>('idle');
  const [loadError, setLoadError] = useState<string | null>(null);

  const spawn = useCallback(() => {
    worker.current?.terminate();
    worker.current = new Worker('/pyodide-worker.js');
    return worker.current;
  }, []);

  const call = useCallback((msg: Record<string, unknown>, timeoutMs: number) =>
    new Promise<Record<string, unknown>>((resolve, reject) => {
      const w = worker.current ?? spawn();
      const id = ++seq.current;
      const timer = setTimeout(() => { w.terminate(); worker.current = null; reject(new Error('timeout')); }, timeoutMs);
      w.onmessage = (e) => { if (e.data.id === id) { clearTimeout(timer); resolve(e.data); } };
      w.onerror = () => { clearTimeout(timer); reject(new Error('worker')); };
      w.postMessage({ ...msg, id });
    }), [spawn]);

  const init = useCallback(async () => {
    setStatus('loading'); setLoadError(null);
    try {
      const r = await call({ type: 'init' }, LOAD_TIMEOUT_MS);
      if (r.type === 'fatal') throw new Error(String(r.message));
      setStatus('ready');
    } catch {
      setStatus('error');
      setLoadError('The browser Python runtime could not load. Check your internet connection and retry. You can still submit for official grading.');
    }
  }, [call]);

  useEffect(() => { void init(); return () => { worker.current?.terminate(); worker.current = null; }; }, [init]);

  const run = useCallback(async (code: string): Promise<PracticeResult> => {
    if (!worker.current) await init();
    setStatus('running');
    try {
      const r = await call({ type: 'run', code }, RUN_TIMEOUT_MS);
      setStatus('ready');
      if (r.type === 'fatal') return { stdout: '', stderr: '', error: 'The Python runtime failed. Please retry.', errorLine: null, truncated: false, timedOut: false };
      return { stdout: String(r.stdout ?? ''), stderr: String(r.stderr ?? ''), error: (r.error as string | null) ?? null, errorLine: (r.line as number | null) ?? null, truncated: Boolean(r.truncated), timedOut: false };
    } catch {
      setStatus('idle'); // worker was terminated; reload lazily
      void init();
      return { stdout: '', stderr: '', error: 'Your code ran for more than 5 seconds and was stopped. Check for a loop that never ends.', errorLine: null, truncated: false, timedOut: true };
    }
  }, [call, init]);

  return { status, loadError, run, retry: init };
}
