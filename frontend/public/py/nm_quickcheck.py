"""Browser quick check (NOT the official result). Runs the learner's code in the page's Python with the lab's files and the
simulated practice API, then evaluates the VISIBLE checks with the grader's own evaluate.py. Hidden checks stay on the server."""
import contextlib
import io
import json
import os
import sys
import traceback

import nm_evaluate

MAX_OUT = 20000


def _plain(v, depth=0):
    if v is None or isinstance(v, (bool, int)):
        return v
    if isinstance(v, float):
        return v if v == v and v not in (float("inf"), float("-inf")) else repr(v)
    if isinstance(v, str):
        return v[:500]
    if depth < 3 and isinstance(v, (list, tuple, set, frozenset)):
        return [_plain(x, depth + 1) for x in list(v)[:50]]
    if depth < 3 and isinstance(v, dict):
        return {str(k)[:80]: _plain(x, depth + 1) for k, x in list(v.items())[:50]}
    try:
        import numbers
        if isinstance(v, numbers.Number):
            return _plain(float(v), depth)
        if hasattr(v, "tolist") and not isinstance(v, str):
            return _plain(v.tolist(), depth)
    except Exception:  # noqa: BLE001
        pass
    return repr(v)[:200]


def _workdir():
    """/lab inside the browser runtime (Pyodide's own in-memory filesystem). Anywhere else (tests, tools) a private
    temporary folder, so nothing is written to the machine's root and no special permission is needed."""
    if sys.platform == "emscripten":
        os.makedirs("/lab", exist_ok=True)
        return "/lab"
    import tempfile
    return tempfile.mkdtemp(prefix="nm-lab-")


def write_files(files):
    os.chdir(_workdir())
    for name, spec in (files or {}).items():
        if not name or "/" in name or name.startswith("."):
            continue
        if isinstance(spec, dict) and spec.get("encoding") == "base64":
            import base64
            data = base64.b64decode(spec.get("content", ""))
        else:
            data = (spec if isinstance(spec, str) else str(spec.get("content", ""))).encode("utf-8")
        with open(name, "wb") as fh:
            fh.write(data)


def run_program(code, capture_vars=(), probes=(), files=None, lab_api=False):
    """Execute and capture: stdout, error (type/message/line), variable summaries and probe values."""
    write_files(files)
    if lab_api:
        import labmock
        labmock.install()
    out = io.StringIO()
    ns = {"__name__": "__main__"}
    error = None
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        try:
            exec(compile(code, "<student>", "exec"), ns)  # noqa: S102
        except BaseException as exc:  # noqa: BLE001
            tb = [f for f in traceback.extract_tb(exc.__traceback__) if f.filename == "<student>"]
            error = {"type": type(exc).__name__, "message": str(exc)[:300], "line": tb[-1].lineno if tb else getattr(exc, "lineno", None)}
    text = out.getvalue()
    truncated = len(text) > MAX_OUT
    vars_ = {}
    for n in capture_vars:
        if n in ns:
            v = ns[n]
            vars_[n] = {"type": type(v).__name__, "value": v if isinstance(v, (str, int, float, bool)) else repr(v)[:200]}
    probes_out = {}
    for expr in probes:
        if error is not None:
            probes_out[expr] = {"ok": False, "error": "not evaluated: the program raised an error"}
            continue
        try:
            probes_out[expr] = {"ok": True, "value": _plain(eval(expr, dict(ns)))}  # noqa: S307
        except BaseException as exc:  # noqa: BLE001
            probes_out[expr] = {"ok": False, "error": (type(exc).__name__ + ": " + str(exc))[:200]}
    return {"stdout": text[:MAX_OUT], "truncated": truncated, "error": error, "vars": vars_, "probes": probes_out}


def quick_check(code, tests_json, files_json=None, lab_api=False):
    tests = json.loads(tests_json)
    files = json.loads(files_json) if files_json else {}
    rows = [{"test_order": t["test_order"], "definition": t["definition"], "points": 1, "is_hidden": False} for t in tests]
    r = run_program(code, nm_evaluate.required_vars(rows), nm_evaluate.probe_exprs(rows), files, lab_api)
    run = nm_evaluate.RunResult("ok", r["stdout"], r["truncated"], r["error"], r["vars"], 0, "", r["probes"])
    res = nm_evaluate.evaluate(rows, run, 100) if rows else {"status": "passed" if not r["error"] else "failed", "criteria": [], "feedback": [], "passed_tests": 0, "total_tests": 0}
    labels = {t["test_order"]: t.get("label") or t["definition"].get("description", "Check") for t in tests}
    res["criteria"] = [{"test_order": c["test_order"], "label": labels.get(c["test_order"], "Check"), "passed": c["passed"]} for c in res.get("criteria", [])]
    res["stdout"], res["error"] = r["stdout"], r["error"]
    return json.dumps(res)
