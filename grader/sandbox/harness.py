"""Runs INSIDE the sandbox container (or, in tests only, a local subprocess).

Reads {"code", "capture_vars", "nonce", "max_output"} as JSON on stdin, executes the student code with
stdout captured, and prints ONE result line: NMRESULT:<nonce>:<json>. Hidden test definitions are never
sent here; the host evaluates them against the captured stdout/variables.

Known limitation (prototype): hostile code running in this process could try to forge the result line.
The container protects the HOST, not the integrity of the learner's own grade.
"""
import contextlib
import io
import json
import sys
import traceback


def main() -> None:
    payload = json.loads(sys.stdin.read())
    nonce, max_out = payload["nonce"], int(payload.get("max_output", 20000))
    names = [n for n in payload.get("capture_vars", []) if isinstance(n, str)]
    real_stdout = sys.stdout
    buf = io.StringIO()
    namespace: dict = {"__name__": "__main__"}
    error = None
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            exec(compile(payload["code"], "<student>", "exec"), namespace)  # noqa: S102
    except BaseException as exc:  # includes SystemExit
        tb = traceback.extract_tb(exc.__traceback__)
        student = [f for f in tb if f.filename == "<student>"]
        line = student[-1].lineno if student else None
        error = {"type": type(exc).__name__, "message": str(exc)[:300], "line": line}
    out = buf.getvalue()
    truncated = len(out) > max_out
    variables = {}
    for n in names:
        if n in namespace:
            v = namespace[n]
            variables[n] = {"type": type(v).__name__, "value": v if isinstance(v, (str, int, float, bool)) else repr(v)[:200]}
    result = {"stdout": out[:max_out], "truncated": truncated, "error": error, "vars": variables}
    real_stdout.write(f"\nNMRESULT:{nonce}:{json.dumps(result)}\n")
    real_stdout.flush()


if __name__ == "__main__":
    main()
