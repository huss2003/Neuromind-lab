/* Browser PRACTICE runtime (not official grading). Runs in a Web Worker so the page can terminate it on timeout. */
const PYODIDE_VERSION = '0.27.4';
importScripts(`https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/pyodide.js`);

const MAX_OUTPUT = 20000;
let pyPromise = null;
const getPy = () => (pyPromise ??= loadPyodide({ indexURL: `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/` }));

onmessage = async (e) => {
  const { id, type, code } = e.data;
  try {
    const py = await getPy();
    if (type === 'init') return postMessage({ id, type: 'ready' });
    let out = '';
    let truncated = false;
    const add = (s) => {
      if (out.length < MAX_OUTPUT) out += s + '\n';
      if (out.length >= MAX_OUTPUT) { out = out.slice(0, MAX_OUTPUT); truncated = true; }
    };
    py.setStdout({ batched: add });
    py.setStderr({ batched: add });
    let error = null;
    try {
      await py.runPythonAsync(code, { globals: py.toPy({}) });
    } catch (err) {
      error = String(err && err.message ? err.message : err).split('\n').slice(-4).join('\n');
    }
    postMessage({ id, type: 'result', stdout: out, truncated, error });
  } catch (err) {
    postMessage({ id, type: 'fatal', message: String(err) });
  }
};
