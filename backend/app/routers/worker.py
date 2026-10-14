"""Private API used ONLY by the grading worker (pull model). The worker authenticates with a dedicated token and holds no
database credentials; it can claim a job, extend its lease, and post a result for the job it claimed. It cannot read any
other data. Disabled (503) unless GRADER_WORKER_TOKEN is configured."""
import hmac
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Header, Request, Response
from pydantic import BaseModel, Field

from app.errors import ApiError
from app.grader_client import GradeResult, InvalidGraderResult, validate_payload
from app.repository import Repository, get_repository
from app.routers.deps import path_uuid
from app.services import metrics
from app.services import audit
from app.services.finalize import finalize_submission

router = APIRouter(prefix="/api/v1/internal/grader")
LEASE_SECONDS = 60
MAX_CLAIMS = 3


def require_worker(x_worker_token: str | None = Header(default=None)) -> None:
    expected = os.getenv("GRADER_WORKER_TOKEN", "")
    if not expected:
        raise ApiError(503, "DEPENDENCY_UNAVAILABLE", "Worker interface is not enabled")
    if not x_worker_token or not hmac.compare_digest(expected, x_worker_token):
        raise ApiError(401, "UNAUTHENTICATED", "Invalid worker credentials")


class ClaimBody(BaseModel):
    worker_id: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.:-]+$")


class ResultBody(ClaimBody):
    result: dict[str, Any]


@router.post("/claim", dependencies=[Depends(require_worker)])
async def claim(body: ClaimBody, repo: Repository = Depends(get_repository)):
    sub = await repo.claim_next_submission(body.worker_id, LEASE_SECONDS, MAX_CLAIMS)
    if not sub:
        return Response(status_code=204)
    tests = await repo.list_exercise_tests(sub["exercise_id"])
    ex = await repo.get_published_exercise(sub["exercise_id"])
    if not ex:  # content was unpublished after submission: hand it back as a platform fault, not a learner failure
        await repo.update_submission(sub["id"], {"status": "error", "claimed_by": None, "lease_expires_at": None, "safe_feedback": [
            {"kind": "infrastructure", "message": "This exercise is no longer available. Your code was not judged."}]})
        return Response(status_code=204)
    return {
        "submission_id": sub["id"], "claim_count": sub["claim_count"], "lease_seconds": LEASE_SECONDS,
        "source_code": sub["source_code"], "pass_threshold": float(ex["pass_threshold"]),
        "timeout_seconds": float(os.getenv("GRADING_TIMEOUT_SECONDS", "5")),
        "tests": [{"test_order": t["test_order"], "definition": t["definition"], "points": float(t["points"]),
                   "is_hidden": t["is_hidden"]} for t in tests]}


async def _owned(repo: Repository, submission_id: str, worker_id: str) -> dict:
    sub = await repo.get_submission(path_uuid(submission_id))
    if not sub or sub.get("claimed_by") != worker_id or sub["status"] not in ("running", "expired"):
        raise ApiError(409, "LEASE_LOST", "This job is no longer assigned to you")
    return sub


@router.post("/jobs/{submission_id}/heartbeat", dependencies=[Depends(require_worker)])
async def heartbeat(submission_id: str, body: ClaimBody, repo: Repository = Depends(get_repository)):
    if not await repo.extend_lease(path_uuid(submission_id), body.worker_id, LEASE_SECONDS):
        raise ApiError(409, "LEASE_LOST", "This job is no longer assigned to you")
    return {"lease_seconds": LEASE_SECONDS}


@router.post("/jobs/{submission_id}/result", dependencies=[Depends(require_worker)])
async def post_result(submission_id: str, body: ResultBody, request: Request, repo: Repository = Depends(get_repository)):
    """Idempotent: a duplicate delivery after finalisation changes nothing and still answers 200."""
    sub = await repo.get_submission(path_uuid(submission_id))
    if sub and sub["status"] in ("passed", "failed", "runtime_error", "timeout", "cancelled"):
        return {"accepted": False, "reason": "already_final"}
    sub = await _owned(repo, submission_id, body.worker_id)
    try:
        result: GradeResult = validate_payload(body.result)
    except InvalidGraderResult:
        await audit.record(repo, request, None, "worker.result_rejected", "submission", sub["id"], {"submission_id": sub["id"]})
        result = GradeResult("error", feedback=[{"kind": "infrastructure", "message": "Grading returned an unreadable result. Your code was not judged. Please try again."}])
    ex = await repo.get_published_exercise(sub["exercise_id"])
    lecture = await repo.get_published_lecture(ex["lecture_id"]) if ex else None
    if not ex or not lecture:
        raise ApiError(409, "CONTENT_CHANGED", "Exercise is no longer published")
    tests = await repo.list_exercise_tests(ex["id"])
    done = await finalize_submission(repo, sub, ex, lecture, result, tests, getattr(request.state, "request_id", None))
    return {"accepted": done}


@router.post("/jobs/{submission_id}/release", dependencies=[Depends(require_worker)])
async def release(submission_id: str, body: ClaimBody, repo: Repository = Depends(get_repository)):
    """The worker could not run the job for an infrastructure reason: put it back (bounded by MAX_CLAIMS)."""
    await _owned(repo, submission_id, body.worker_id)
    return {"released": await repo.release_submission(path_uuid(submission_id), body.worker_id)}


@router.get("/health", dependencies=[Depends(require_worker)])
async def queue_health(repo: Repository = Depends(get_repository)):
    """Queue depth and the age of the oldest waiting job, for monitoring. Counts only; no learner data."""
    since = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    recent = metrics.summarise(await repo.queue_metrics(since))
    return {**await repo.queue_stats(), "queue_wait_p95_seconds": recent["queue_wait_seconds"]["p95"],
            "execution_p95_seconds": recent["execution_seconds"]["p95"], "sample_last_hour": recent["sample"]}
