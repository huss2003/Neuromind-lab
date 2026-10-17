"""Host-side test evaluation. Test definitions (incl. hidden ones) never enter the sandbox; only probe EXPRESSIONS do
(their expected values stay here)."""
import math
import re
from dataclasses import dataclass, field
from typing import Any

GRADER_VERSION = "1.2.0"
HARNESS_VERSION = 2  # announced on every claim: 2 = probes, lab data files, practice API, lab limits


@dataclass
class RunResult:
    status: str  # ok | timeout | infra_error | crashed
    stdout: str = ""
    truncated: bool = False
    error: dict[str, Any] | None = None
    vars: dict[str, Any] = field(default_factory=dict)
    execution_ms: int = 0
    detail: str = ""
    probes: dict[str, Any] = field(default_factory=dict)  # expression -> {"ok": bool, "value"|"error"}


class UnsupportedTest(Exception):
    pass


def required_vars(tests: list[dict]) -> list[str]:
    return sorted({t["definition"]["name"] for t in tests if isinstance(t["definition"].get("name"), str)})


def probe_exprs(tests: list[dict]) -> list[str]:
    """Ordered, de-duplicated probe expressions. These are the only part of a test that reaches the sandbox."""
    out: list[str] = []
    for t in tests:
        e = t["definition"].get("expr")
        if isinstance(e, str) and e and e not in out:
            out.append(e)
    return out


def _close(a: Any, b: Any) -> bool:
    """Equality that is forgiving about int/float, float noise and surrounding whitespace in strings."""
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b or a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=1e-6, abs_tol=1e-6)
    if isinstance(a, str) and isinstance(b, str):
        return a.strip() == b.strip()
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_close(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(_close(a[k], b[k]) for k in a)
    return a == b


def _lines(out: str) -> list[str]:
    return [ln.rstrip() for ln in out.splitlines() if ln.strip()]


def check(defn: dict, run: RunResult) -> bool:
    out = run.stdout.strip()
    if defn.get("match") == "non_empty":
        return out != ""
    if "expected_stdout" in defn:
        return out == str(defn["expected_stdout"]).strip()
    if "expected_stdout_lines" in defn:
        want = [str(x).strip() for x in defn["expected_stdout_lines"]]
        return [ln.strip() for ln in _lines(run.stdout)] == want
    if "stdout_contains" in defn:
        needle, hay = str(defn["stdout_contains"]), run.stdout
        if defn.get("ignore_case"):
            needle, hay = needle.lower(), hay.lower()
        return needle in hay
    if "stdout_regex" in defn:
        return re.search(str(defn["stdout_regex"]), run.stdout, re.MULTILINE | (re.IGNORECASE if defn.get("ignore_case") else 0)) is not None
    if "stdout_min_lines" in defn:
        return len(_lines(run.stdout)) >= int(defn["stdout_min_lines"])
    if "expr" in defn:
        probe = run.probes.get(str(defn["expr"]))
        if not probe or not probe.get("ok"):
            return False
        value = probe.get("value")
        if "expected" in defn:
            return _close(value, defn["expected"])
        if "expected_in" in defn:
            return any(_close(value, x) for x in defn["expected_in"])
        if defn.get("truthy", True):
            return bool(value) is True
        return value is False or not value
    kind, name = defn.get("check"), defn.get("name")
    if kind == "variable_is_str":
        return run.vars.get(name, {}).get("type") == "str"
    if kind == "variable_type":
        return run.vars.get(name, {}).get("type") == defn.get("type")
    if kind == "stdout_equals_variable":
        v = run.vars.get(name)
        return bool(v) and v["type"] == "str" and out == v["value"].strip()
    if kind == "variable_equals":
        v = run.vars.get(name)
        return bool(v) and _close(v["value"], defn.get("value"))
    raise UnsupportedTest(str(defn.get("description", "unknown test")))


def evaluate(tests: list[dict], run: RunResult, pass_threshold: float) -> dict[str, Any]:
    total_points = sum(float(t["points"]) for t in tests) or 1.0
    feedback: list[dict[str, str]] = []

    if run.status == "timeout":
        return {"status": "timeout", "passed_tests": 0, "total_tests": len(tests), "score": 0.0,
                "execution_ms": run.execution_ms,
                "feedback": [{"kind": "failure", "message": "Your program took too long and was stopped. Check for loops that never end."}]}
    if run.status == "infra_error":
        return {"status": "error", "passed_tests": 0, "total_tests": len(tests), "score": None,
                "execution_ms": run.execution_ms,
                "feedback": [{"kind": "infrastructure", "message": "The grading sandbox is unavailable. Your code was not judged. Please try again."}]}
    if run.status == "crashed":
        return {"status": "failed", "passed_tests": 0, "total_tests": len(tests), "score": 0.0,
                "execution_ms": run.execution_ms,
                "feedback": [{"kind": "failure", "message": run.detail or "Your program stopped unexpectedly (possibly too much memory)."}]}

    if run.error:
        e = run.error
        where = f" on line {e['line']}" if e.get("line") else ""
        feedback.append({"kind": "failure", "message": f"Your program raised {e['type']}{where}: {e['message']}"})
    if run.truncated:
        feedback.append({"kind": "info", "message": "Your output was very long and was cut off."})

    earned, passed = 0.0, 0
    criteria: list[dict[str, Any]] = []
    for t in sorted(tests, key=lambda x: x["test_order"]):
        try:
            ok = check(t["definition"], run) if not run.error else False
        except UnsupportedTest:
            return {"status": "error", "passed_tests": 0, "total_tests": len(tests), "score": None,
                    "execution_ms": run.execution_ms,
                    "feedback": [{"kind": "infrastructure", "message": "This exercise has a test configuration problem. Please tell your teacher."}]}
        label = "A hidden test" if t["is_hidden"] else str(t["definition"].get("description", f"Test {t['test_order']}"))
        criteria.append({"test_order": t["test_order"], "passed": bool(ok)})
        if ok:
            earned += float(t["points"])
            passed += 1
        if not run.error:  # avoid piling on after a crash
            feedback.append({"kind": "success" if ok else "failure", "message": f"{label}: {'passed' if ok else 'not passed yet'}"})
    score = round(100 * earned / total_points, 2)
    status = "passed" if score >= pass_threshold and not run.error else "failed"
    if status == "passed":
        feedback.insert(0, {"kind": "success", "message": "All required tests passed." if passed == len(tests) else "You reached the pass mark."})
    return {"status": status, "passed_tests": passed, "total_tests": len(tests), "score": score,
            "execution_ms": run.execution_ms, "feedback": feedback, "criteria": criteria,
            "grader_version": GRADER_VERSION, "runtime_error": bool(run.error)}
