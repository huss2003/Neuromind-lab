"""Runs INSIDE the sandbox container (or, in tests only, a local subprocess).

Two processes, one trust boundary:

* PARENT (this file's `main`): trusted. Reads {"code","capture_vars","nonce","max_output"} from stdin, then starts a
  CHILD process for the learner code. The nonce exists only in the parent's memory; it is never passed to the child
  (not in argv, env, stdin or files), and the parent marks itself non-dumpable so the child cannot read it through
  /proc/<ppid>/mem. The parent emits the single result line NMRESULT:<nonce>:<json>.
* CHILD (`CHILD_SOURCE`): untrusted. Runs the learner code. Whatever it prints is captured by the PARENT from the
  child's real stdout pipe, so printing a fake result line is just ordinary (and ignored-as-control) output.
  The child reports variable values and an error summary on a separate pipe (an inherited pipe fd). That report is treated as
  untrusted DATA: it is size-limited and strictly schema-validated, and a missing/duplicate/malformed report makes
  the run "crashed", never "passed".

What this does NOT prove: variable values are reported by the learner process, so a learner can claim a value for a
variable; the host's checks are on observable behaviour (stdout and variable values the program could legitimately
set), so this gives a learner nothing they could not do by writing the right program. Hidden tests never enter the
sandbox; the host evaluates them.
"""
import json
import os
import select
import subprocess
import sys

MAX_REPORT_BYTES = 100_000
SCALARS = (str, int, float, bool)

CHILD_SOURCE = r'''
import json, os, sys, traceback
req = json.loads(sys.stdin.read())
sys.stdin = open(os.devnull)
ns = {"__name__": "__main__"}
error = None
try:
    exec(compile(req["code"], "<student>", "exec"), ns)  # noqa: S102
except BaseException as exc:
    tb = [f for f in traceback.extract_tb(exc.__traceback__) if f.filename == "<student>"]
    error = {"type": type(exc).__name__, "message": str(exc)[:300], "line": tb[-1].lineno if tb else None}
vars_ = {}
for n in req["capture_vars"]:
    if n in ns:
        v = ns[n]
        vars_[n] = {"type": type(v).__name__, "value": v if isinstance(v, (str, int, float, bool)) else repr(v)[:200]}
sys.stdout.flush()
with os.fdopen(int(sys.argv[1]), "w") as report:
    report.write(json.dumps({"error": error, "vars": vars_}))
'''


def _harden_parent() -> None:
    """Best effort: stop the child from reading this process's memory via /proc or ptrace."""
    try:
        import ctypes
        ctypes.CDLL(None).prctl(4, 0, 0, 0, 0)  # PR_SET_DUMPABLE = 0
    except Exception:  # noqa: BLE001 - hardening only; absence is reported by the adversarial tests
        pass


def validate_report(raw: bytes, names: list[str]) -> dict | None:
    """Strict schema check of the child's untrusted report. None = reject."""
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict) or set(data) != {"error", "vars"}:
        return None
    err, variables = data["error"], data["vars"]
    if err is not None:
        if not isinstance(err, dict) or set(err) != {"type", "message", "line"}:
            return None
        if not (isinstance(err["type"], str) and isinstance(err["message"], str) and (err["line"] is None or isinstance(err["line"], int))):
            return None
        err = {"type": err["type"][:80], "message": err["message"][:300], "line": err["line"]}
    if not isinstance(variables, dict):
        return None
    clean: dict = {}
    for name, entry in variables.items():
        if name not in names or not isinstance(entry, dict) or set(entry) != {"type", "value"}:
            return None
        if not isinstance(entry["type"], str):
            return None
        value = entry["value"]
        if not isinstance(value, SCALARS):
            return None
        clean[name] = {"type": entry["type"][:40], "value": value[:200] if isinstance(value, str) else value}
    return {"error": err, "vars": clean}


def run_child(code: str, names: list[str], max_out: int) -> tuple[bytes, bool, bytes | None, int | None]:
    """Run learner code. Returns (stdout, truncated, report_bytes, exit_code)."""
    r_fd, w_fd = os.pipe()
    child = subprocess.Popen(  # noqa: S603 - fixed argv, learner code travels over stdin only
        [sys.executable, "-I", "-c", CHILD_SOURCE, str(w_fd)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, pass_fds=(w_fd,), env={}, close_fds=True)
    os.close(w_fd)
    assert child.stdin is not None and child.stdout is not None
    try:
        child.stdin.write(json.dumps({"code": code, "capture_vars": names}).encode())
        child.stdin.close()
    except BrokenPipeError:
        pass
    out, report, truncated = b"", b"", False
    open_fds = {child.stdout.fileno(): "out", r_fd: "report"}
    while open_fds:
        ready, _, _ = select.select(list(open_fds), [], [], 0.5)
        for fd in ready:
            chunk = os.read(fd, 65536)
            if not chunk:
                del open_fds[fd]
                continue
            if open_fds[fd] == "out":
                room = max_out - len(out)
                out += chunk[:max(room, 0)]
                if len(chunk) > room:
                    truncated = True  # keep draining (and discarding) so the program is never blocked and the report still arrives
            else:
                report += chunk
                if len(report) > MAX_REPORT_BYTES:
                    child.kill()
                    open_fds.pop(fd, None)
                    report = b"x" * (MAX_REPORT_BYTES + 1)
    code_out = child.wait()
    os.close(r_fd)
    return out, truncated, (report if report and len(report) <= MAX_REPORT_BYTES else None), code_out


def main() -> None:
    _harden_parent()
    payload = json.loads(sys.stdin.read())
    nonce, max_out = payload["nonce"], int(payload.get("max_output", 20000))
    names = [n for n in payload.get("capture_vars", []) if isinstance(n, str)]
    out, truncated, report_raw, _exit_code = run_child(payload["code"], names, max_out)
    report = validate_report(report_raw, names) if report_raw is not None else None
    if report is None:
        # Missing/forged/malformed report: fail safe. The host maps a missing result line to "crashed".
        sys.stdout.write("\n")
        sys.exit(3)
    result = {"stdout": out.decode("utf-8", "replace"), "truncated": truncated, "error": report["error"], "vars": report["vars"]}
    sys.stdout.write(f"\nNMRESULT:{nonce}:{json.dumps(result)}\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
