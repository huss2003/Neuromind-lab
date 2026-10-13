import os
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Header
from pydantic import BaseModel

from app.auth import CurrentUser, current_user
from app.errors import ApiError
from app.grader_client import Grader, get_grader
from app.repository import Repository, get_repository
from app.routers.deps import idempotency_key, path_uuid
from app.services.context import load_context
from app.services.progress import max_reachable_order

router = APIRouter(prefix="/api/v1")
STALE_AFTER_SECONDS = 120
COUNTED = ("passed", "failed", "timeout")  # infrastructure errors never consume an attempt


def _max_bytes() -> int:
    return int(os.getenv("MAX_SOURCE_CODE_BYTES", "50000"))


async def _exercise_ctx(repo: Repository, user_id: str, exercise_id: str):
    ex = await repo.get_published_exercise(exercise_id)
    if not ex:
        raise ApiError(404, "NOT_FOUND")
    ctx = await load_context(repo, user_id, ex["lecture_id"])
    segment = next((s for s in ctx.segments if s.get("exercise_id") == exercise_id), None)
    if not segment:
        raise ApiError(500, "CONTENT_CONFIGURATION_ERROR", "Exercise is not part of the lecture")
    return ex, ctx, segment


@router.get("/exercises/{exercise_id}")
async def get_exercise(exercise_id: str, user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)):
    ex, _, _ = await _exercise_ctx(repo, user.id, path_uuid(exercise_id))
    return {"id": ex["id"], "title": ex["title"], "instructions": ex["instructions"], "language": ex["language"],
            "starter_code": ex["starter_code"], "practice_mode": ex["practice_mode"],
            "pass_threshold": float(ex["pass_threshold"]), "max_attempts": ex["max_attempts"]}


class SubmissionBody(BaseModel):
    source_code: str


def _view(sub: dict) -> dict:
    status = sub["status"]
    return {"submission_id": sub["id"], "submission_number": sub["submission_number"], "status": status,
            "score": float(sub["score"]) if sub["score"] is not None else None,
            "passed_tests": sub["passed_tests"], "total_tests": sub["total_tests"],
            "execution_ms": sub["execution_ms"], "feedback": sub["safe_feedback"],
            "infrastructure_error": status == "error", "created_at": sub["created_at"]}


async def _run_grading(repo: Repository, grader: Grader, sub: dict, ex: dict) -> None:
    await repo.update_submission(sub["id"], {"status": "running"})
    try:
        tests = await repo.list_exercise_tests(ex["id"])
        result = await grader.grade(sub["source_code"], tests, float(ex["pass_threshold"]))
    except Exception:  # never leave a submission stuck, never blame the learner
        from app.grader_client import GradeResult
        result = GradeResult("error", feedback=[{"kind": "infrastructure", "message": "Grading failed to run. Please try again."}])
    await repo.update_submission(sub["id"], {
        "status": result.status, "score": result.score, "passed_tests": result.passed_tests,
        "total_tests": result.total_tests, "execution_ms": result.execution_ms, "safe_feedback": result.feedback})


@router.post("/exercises/{exercise_id}/submissions", status_code=202)
async def create_submission(exercise_id: str, body: SubmissionBody, background: BackgroundTasks,
                            user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository),
                            grader: Grader = Depends(get_grader),
                            idempotency_key_header: str | None = Header(default=None, alias="Idempotency-Key")):
    exercise_id = path_uuid(exercise_id)
    key = idempotency_key(idempotency_key_header)
    ex, ctx, segment = await _exercise_ctx(repo, user.id, exercise_id)
    if len(body.source_code.encode()) > _max_bytes() or not body.source_code.strip():
        raise ApiError(422, "VALIDATION_ERROR", details=[{"field": "source_code", "issue": "Empty or too large"}])

    existing = await repo.find_submission_by_key(user.id, key)
    if existing:
        if existing["exercise_id"] != exercise_id or existing["source_code"] != body.source_code:
            raise ApiError(409, "IDEMPOTENCY_CONFLICT", "Idempotency key reused with a different request")
        return {"submission_id": existing["id"], "status": existing["status"],
                "status_url": f"/api/v1/submissions/{existing['id']}"}

    if segment["segment_order"] > max_reachable_order(ctx.segments, ctx.checkpoints, ctx.progress):
        raise ApiError(400, "CHECKPOINT_REQUIRED", "Complete earlier required checkpoints first")
    counted = [s for s in ctx.submissions if s["exercise_id"] == exercise_id and s["status"] in COUNTED]
    if ex["max_attempts"] is not None and len(counted) >= ex["max_attempts"]:
        raise ApiError(409, "ATTEMPTS_EXHAUSTED", "No attempts remaining for this exercise")

    sub = await repo.insert_submission({
        "learner_id": user.id, "exercise_id": exercise_id, "source_code": body.source_code,
        "idempotency_key": key, "status": "queued"})
    background.add_task(_run_grading, repo, grader, sub, ex)
    return {"submission_id": sub["id"], "status": "queued", "status_url": f"/api/v1/submissions/{sub['id']}"}


@router.get("/submissions/{submission_id}")
async def get_submission(submission_id: str, user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)):
    sub = await repo.get_submission(path_uuid(submission_id))
    # Owner, or teacher/admin. Anyone else gets 404 (not 403) so ids can't be probed.
    if not sub or (sub["learner_id"] != user.id and user.role not in ("teacher", "admin")):
        raise ApiError(404, "NOT_FOUND")
    if sub["status"] in ("queued", "running"):
        created = datetime.fromisoformat(str(sub["created_at"]).replace("Z", "+00:00"))
        if (datetime.now(UTC) - created).total_seconds() > STALE_AFTER_SECONDS:
            sub = await repo.update_submission(sub["id"], {"status": "error", "safe_feedback": [
                {"kind": "infrastructure", "message": "Grading did not finish. Your code was not judged. Please retry."}]}) or sub
    return _view(sub)


@router.get("/exercises/{exercise_id}/submissions")
async def list_my_submissions(exercise_id: str, user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)):
    subs = await repo.list_submissions(user.id, [path_uuid(exercise_id)])
    return {"submissions": [_view(s) for s in subs]}
