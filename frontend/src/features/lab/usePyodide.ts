import { useCallback, useEffect, useRef, useState } from 'react';
import type { LabAsset, VisibleCheck } from '../../services/types';

export type RuntimeStatus = 'idle' | 'loading' | 'ready' | 'running' | 'error';
export interface PracticeResult { stdout: string; stderr: string; error: string | null; errorLine: number | null; truncated: boolean; timedOut: boolean }
export interface QuickCheckResult {
  status: 'passed' | 'failed' | 'timeout' | 'unavailable';
  criteria: { test_order: number; label: string; passed: boolean }[];
  error: { type: string; message: string; line: number | null } | null;
  stdout: string;
}
export interface RuntimeOptions { packages?: string[]; assets?: LabAsset[]; labApi?: boolean }

const LOAD_TIMEOUT_MS = 180_000; // scientific packages are tens of MB on first load
export const RUN_TIMEOUT_MS = 5_000;
const HEAVY = ['numpy', 'pandas', 'matplotlib', 'scikit-learn', 'pillow'];
const filesOf = (assets?: LabAsset[]) => Object.fromEntries((assets ?? []).map((a) => [a.name, a.encoding === 'base64' ? { encoding: 'base64', content: a.content } : a.content]));

/** Owns a terminable Pyodide worker. A timed-out run terminates the worker and a fresh one loads on demand. */
export function usePyodide(options: RuntimeOptions = {}) {
  const worker = useRef<Worker | null>(null);
  const seq = useRef(0);
  const opts = useRef(options);
  opts.current = options;
  const [status, setStatus] = useState<RuntimeStatus>('idle');
  const [loadError, setLoadError] = useState<string | null>(null);
  const packagesKey = (options.packages ?? []).join(',');
  const runTimeout = (options.packages ?? []).some((p) => HEAVY.includes(p)) ? 30_000 : RUN_TIMEOUT_MS;

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
      const r = await call({ type: 'init', packages: opts.current.packages ?? [] }, LOAD_TIMEOUT_MS);
      if (r.type === 'fatal') throw new Error(String(r.message));
      setStatus('ready');
    } catch {
      setStatus('error');
      setLoadError('The browser Python runtime could not load. Check your internet connection and retry. You can still save and check your work officially.');
    }
  }, [call]);

   
  useEffect(() => { void init(); return () => { worker.current?.terminate(); worker.current = null; }; }, [init, packagesKey]);

  const timedOutResult = (): PracticeResult => ({ stdout: '', stderr: '', error: `Your code ran for more than ${runTimeout / 1000} seconds and was stopped. Check for a loop that never ends.`, errorLine: null, truncated: false, timedOut: true });

  const run = useCallback(async (code: string): Promise<PracticeResult> => {
    if (!worker.current) await init();
    setStatus('running');
    try {
      const r = await call({ type: 'run', code, packages: opts.current.packages ?? [], files: filesOf(opts.current.assets), labApi: Boolean(opts.current.labApi) }, runTimeout);
      setStatus('ready');
      if (r.type === 'fatal') return { stdout: '', stderr: '', error: 'The Python runtime failed. Please retry.', errorLine: null, truncated: false, timedOut: false };
      return { stdout: String(r.stdout ?? ''), stderr: String(r.stderr ?? ''), error: (r.error as string | null) ?? null, errorLine: (r.line as number | null) ?? null, truncated: Boolean(r.truncated), timedOut: false };
    } catch {
      setStatus('idle'); // worker was terminated; reload lazily
      void init();
      return timedOutResult();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [call, init, runTimeout]);

  /** Instant check of the VISIBLE criteria, in the browser. Never an official result. */
  const check = useCallback(async (code: string, tests: VisibleCheck[]): Promise<QuickCheckResult> => {
    if (status === 'error' || status === 'loading') return { status: 'unavailable', criteria: [], error: null, stdout: '' };
    if (!worker.current) await init();
    setStatus('running');
    try {
      const r = await call({ type: 'check', code, tests, packages: opts.current.packages ?? [], files: filesOf(opts.current.assets), labApi: Boolean(opts.current.labApi) }, runTimeout);
      setStatus('ready');
      if (r.type === 'fatal') return { status: 'unavailable', criteria: [], error: null, stdout: '' };
      return { status: (r.status as 'passed' | 'failed') ?? 'failed', criteria: (r.criteria as QuickCheckResult['criteria']) ?? [], error: (r.error as QuickCheckResult['error']) ?? null, stdout: String(r.stdout ?? '') };
    } catch {
      setStatus('idle');
      void init();
      return { status: 'timeout', criteria: [], error: { type: 'Timeout', message: `Your code ran for more than ${runTimeout / 1000} seconds and was stopped.`, line: null }, stdout: '' };
    }
     
  }, [call, init, runTimeout, status]);

  return { status, loadError, run, check, retry: init, runTimeout };
}
