"""Grading adapter. The API never executes student code; it calls a separate grader service
(local Docker worker in the prototype). Swap this class for a hosted worker later."""
import os
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx


@dataclass
class GradeResult:
    status: str  # passed | failed | timeout | error (error == infrastructure failure)
    passed_tests: int = 0
    total_tests: int = 0
    score: float | None = None
    execution_ms: int | None = None
    feedback: list[dict[str, str]] = field(default_factory=list)
    criteria: list[dict[str, Any]] = field(default_factory=list)
    grader_version: str | None = None
    runtime_error: bool = False


ALLOWED_STATUSES = {"passed", "failed", "timeout", "error"}


class InvalidGraderResult(ValueError):
    pass


def validate_payload(d: Any) -> GradeResult:
    """§9 step 8: only a well-formed, bounded result is accepted; anything else is treated as an infrastructure failure."""
    if not isinstance(d, dict) or d.get("status") not in ALLOWED_STATUSES:
        raise InvalidGraderResult("status")
    def num(v: Any, lo: float, hi: float, name: str, none_ok: bool = False) -> Any:
        if v is None and none_ok:
            return None
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not lo <= v <= hi:
            raise InvalidGraderResult(name)
        return v
    passed = int(num(d.get("passed_tests", 0), 0, 1000, "passed_tests"))
    total = int(num(d.get("total_tests", 0), 0, 1000, "total_tests"))
    if passed > total:
        raise InvalidGraderResult("counts")
    score = num(d.get("score"), 0, 100, "score", none_ok=True)
    ms = num(d.get("execution_ms"), 0, 3_600_000, "execution_ms", none_ok=True)
    fb = d.get("feedback", [])
    crit = d.get("criteria", [])
    if not isinstance(fb, list) or len(fb) > 50 or not isinstance(crit, list) or len(crit) > 200:
        raise InvalidGraderResult("lists")
    feedback = []
    for f in fb:
        if not isinstance(f, dict) or not isinstance(f.get("message"), str):
            raise InvalidGraderResult("feedback")
        feedback.append({"kind": str(f.get("kind", "info"))[:20], "message": f["message"][:500]})
    criteria = []
    for c in crit:
        if not isinstance(c, dict) or not isinstance(c.get("test_order"), int) or not isinstance(c.get("passed"), bool):
            raise InvalidGraderResult("criteria")
        criteria.append({"test_order": c["test_order"], "passed": c["passed"]})
    return GradeResult(d["status"], passed, total, None if score is None else float(score), None if ms is None else int(ms),
                       feedback, criteria, str(d.get("grader_version") or "")[:40] or None, bool(d.get("runtime_error", False)))


class Grader(Protocol):
    async def grade(self, source_code: str, tests: list[dict[str, Any]], pass_threshold: float) -> GradeResult: ...


class HttpGrader:
    async def grade(self, source_code, tests, pass_threshold):
        base = os.getenv("GRADER_BASE_URL", "http://127.0.0.1:8010")
        secret = os.getenv("GRADER_SHARED_SECRET", "")
        payload = {
            "source_code": source_code,
            "tests": [{"test_order": t["test_order"], "definition": t["definition"], "points": float(t["points"]),
                       "is_hidden": t["is_hidden"]} for t in tests],
            "pass_threshold": float(pass_threshold),
            "timeout_seconds": float(os.getenv("GRADING_TIMEOUT_SECONDS", "5")),
        }
        try:
            async with httpx.AsyncClient(timeout=float(os.getenv("GRADING_TIMEOUT_SECONDS", "5")) + 25) as c:
                r = await c.post(f"{base}/grade", json=payload, headers={"X-Grader-Secret": secret})
            if r.status_code != 200:
                raise httpx.HTTPError(f"grader status {r.status_code}")
            return validate_payload(r.json())
        except (httpx.HTTPError, KeyError, ValueError, TypeError):
            # Infrastructure failure: never reported as a learner failure.
            return GradeResult("error", feedback=[{"kind": "infrastructure",
                                                   "message": "The grading service is unavailable. Your code was not judged. Please try again."}])


def get_grader() -> Grader:
    return HttpGrader()
