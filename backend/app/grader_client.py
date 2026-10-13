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
            d = r.json()
            return GradeResult(d["status"], d.get("passed_tests", 0), d.get("total_tests", 0), d.get("score"),
                               d.get("execution_ms"), d.get("feedback", []))
        except (httpx.HTTPError, KeyError, ValueError):
            # Infrastructure failure: never reported as a learner failure.
            return GradeResult("error", feedback=[{"kind": "infrastructure",
                                                   "message": "The grading service is unavailable. Your code was not judged. Please try again."}])


def get_grader() -> Grader:
    return HttpGrader()
