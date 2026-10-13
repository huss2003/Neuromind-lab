"""Single place where an official result becomes the stored result. Used by inline grading and by the worker API."""
from datetime import UTC, datetime
from typing import Any

from app.grader_client import GradeResult
from app.repository import Repository
from app.services import audit
from app.services.grading import apply_hint_penalty, build_criteria, decide_status

Row = dict[str, Any]
FINAL = ("passed", "failed", "runtime_error", "timeout", "cancelled")  # a late result must never overwrite these


async def finalize_submission(repo: Repository, sub: Row, ex: Row, lecture: Row, result: GradeResult, tests: list[Row],
                              request_id: str | None) -> bool:
    """Persist the official result. Idempotent: returns False (and changes nothing) if the attempt is already final."""
    current = await repo.get_submission(sub["id"]) or sub
    if current["status"] in FINAL:
        return False
    section_titles = {x["id"]: x["title"] for x in await repo.list_segments(lecture["id"])}
    hints_used = len(await repo.list_hint_reveals(sub["learner_id"], ex["id"], sub["submission_number"]))
    raw = result.score
    adjusted: float | None = None
    penalty = 0.0
    if raw is not None and result.status in ("passed", "failed"):
        adjusted, penalty = apply_hint_penalty(raw, hints_used, float(ex.get("hint_penalty_percent") or 0))
    else:
        adjusted = raw
    status = decide_status(result.status, adjusted, float(ex["pass_threshold"]), result.runtime_error)
    feedback = list(result.feedback)
    if penalty > 0:
        feedback.append({"kind": "info", "message": f"Hints used: {hints_used}. This attempt's score was reduced by {penalty:g} points. Your best earlier score is unchanged."})
    if status == "failed" and result.status == "passed":
        feedback.append({"kind": "failure", "message": "Your code passed the checks, but hint use brought this attempt below the pass mark. Try again without hints to earn the pass."})
    await repo.update_submission(sub["id"], {
        "status": status, "score": adjusted, "raw_score": raw, "hints_used": hints_used, "hint_penalty": penalty,
        "passed_tests": result.passed_tests, "total_tests": result.total_tests, "execution_ms": result.execution_ms,
        "safe_feedback": feedback, "criteria_results": build_criteria(tests, result.criteria, section_titles),
        "grader_version": result.grader_version, "test_suite_version": ex.get("test_suite_version"),
        "content_version": lecture.get("content_version"), "pass_threshold": ex["pass_threshold"], "max_score": 100,
        "correlation_id": request_id, "finished_at": datetime.now(UTC).isoformat(),
        "claimed_by": None, "lease_expires_at": None})
    await audit.record(repo, None, sub["learner_id"], "submission.finished", "submission", sub["id"],
                       {"status": status, "score": adjusted, "submission_id": sub["id"]})
    return True
