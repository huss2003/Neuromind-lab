/* Browser PRACTICE runtime (not official grading). Runs in a Web Worker so the page can terminate it on timeout. */
const PYODIDE_VERSION = '0.27.4';
importScripts(`https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/pyodide.js`);

const MAX_OUTPUT = 20000;
let pyPromise = null;
const getPy = () => (pyPromise ??= loadPyodide({ indexURL: `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/` }));

function limiter() {
  let text = '';
  let truncated = false;
  return {
    add(line) {
      if (text.length >= MAX_OUTPUT) { truncated = true; return; }
      text += line + '\n';
      if (text.length > MAX_OUTPUT) { text = text.slice(0, MAX_OUTPUT); truncated = true; }
    },
    get text() { return text; },
    get truncated() { return truncated; },
  };
}

onmessage = async (e) => {
  const { id, type, code } = e.data;
  try {
    const py = await getPy();
    if (type === 'init') return postMessage({ id, type: 'ready' });
    const out = limiter();
    const err = limiter();
    py.setStdout({ batched: (s) => out.add(s) });
    py.setStderr({ batched: (s) => err.add(s) });
    let error = null;
    let line = null;
    try {
      await py.runPythonAsync(code, { globals: py.toPy({}) });
    } catch (ex) {
      const msg = String(ex && ex.message ? ex.message : ex);
      error = msg.split('\n').filter(Boolean).slice(-3).join('\n');
      const m = msg.match(/File "<exec>", line (\d+)/);
      if (m) line = Number(m[1]);
    }
    postMessage({ id, type: 'result', stdout: out.text, stderr: err.text, truncated: out.truncated || err.truncated, error, line });
  } catch (ex) {
    postMessage({ id, type: 'fatal', message: String(ex) });
  }
};
