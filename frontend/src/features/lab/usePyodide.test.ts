import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { usePyodide } from './usePyodide';

// A fake browser worker: answers 'init' only when the test releases it, and 'check' at once.
let releaseInit: () => void = () => undefined;
class FakeWorker {
  onmessage: ((e: { data: Record<string, unknown> }) => void) | null = null;
  onerror: (() => void) | null = null;
  postMessage(msg: { id: number; type: string }) {
    const reply = (data: Record<string, unknown>) => this.onmessage?.({ data: { id: msg.id, ...data } });
    if (msg.type === 'init') releaseInit = () => reply({ type: 'ready' });
    if (msg.type === 'check') setTimeout(() => reply({ type: 'checked', status: 'failed', criteria: [{ test_order: 1, label: 'name holds your name', passed: false }], error: null, stdout: '' }), 0);
  }
  terminate() { /* nothing to stop */ }
}

describe('usePyodide quick check', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('waits for Python to finish loading instead of reporting the check as unavailable', async () => {
    vi.stubGlobal('Worker', FakeWorker);
    const { result } = renderHook(() => usePyodide({}));
    expect(result.current.status).toBe('loading');
    let verdict: Awaited<ReturnType<typeof result.current.check>> | undefined;
    await act(async () => {
      const pending = result.current.check('print(1)', []);
      releaseInit(); // Python finishes loading after Save & check was pressed
      verdict = await pending;
    });
    expect(verdict?.status).toBe('failed');
    expect(verdict?.criteria[0].label).toBe('name holds your name');
  });
});
