/* Browser PRACTICE runtime (not official grading). Runs in a Web Worker so the page can terminate it on timeout.
   Loads the lab's packages, writes its data files, mounts the simulated practice API (labmock) and can run the
   grader's VISIBLE checks for the instant "quick check". The server remains the only source of official results. */
const PYODIDE_VERSION = '0.27.4';
importScripts(`https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/pyodide.js`);

const MAX_OUTPUT = 20000;
const PACKAGE_NAMES = { numpy: 'numpy', pandas: 'pandas', matplotlib: 'matplotlib', 'scikit-learn': 'scikit-learn', pillow: 'pillow', requests: 'requests' };
let pyPromise = null;
let loadedPackages = new Set();
let shimReady = false;
const getPy = () => (pyPromise ??= loadPyodide({ indexURL: `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/` }));

async function ensureShim(py) {
  if (shimReady) return;
  for (const name of ['nm_evaluate', 'labmock', 'nm_quickcheck']) {
    const res = await fetch(`/py/${name}.py`);
    if (!res.ok) throw new Error(`cannot load ${name}`);
    py.FS.writeFile(`/lib/python3.12/site-packages/${name}.py`, await res.text());
  }
  shimReady = true;
}

async function ensurePackages(py, packages) {
  const wanted = (packages || []).map((p) => PACKAGE_NAMES[p]).filter((p) => p && !loadedPackages.has(p));
  if (wanted.length) {
    await py.loadPackage(wanted);
    wanted.forEach((p) => loadedPackages.add(p));
  }
}

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
  const { id, type, code, packages, files, labApi, tests } = e.data;
  try {
    const py = await getPy();
    await ensureShim(py);
    await ensurePackages(py, packages);
    if (type === 'init') return postMessage({ id, type: 'ready', packages: [...loadedPackages] });
    if (type === 'check') {
      const quick = py.pyimport('nm_quickcheck');
      const raw = quick.quick_check(code, JSON.stringify(tests || []), JSON.stringify(files || {}), Boolean(labApi));
      const result = JSON.parse(raw);
      return postMessage({ id, type: 'check', ...result });
    }
    const out = limiter();
    const err = limiter();
    py.setStdout({ batched: (s) => out.add(s) });
    py.setStderr({ batched: (s) => err.add(s) });
    let error = null;
    let line = null;
    try {
      const prelude = py.pyimport('nm_quickcheck');
      prelude.write_files(py.toPy(files || {}));
      if (labApi) py.pyimport('labmock').install();
      await py.runPythonAsync(code, { globals: py.toPy({ __name__: '__main__' }) });
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
