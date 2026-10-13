import hashlib
import os
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Request
from pydantic import BaseModel, Field

from app.auth import CurrentUser, current_user
from app.errors import ApiError
from app.grader_client import GradeResult, Grader, get_grader
from app.repository import Repository, get_repository
from app.routers.deps import idempotency_key, path_uuid
from app.services import audit
from app.services.context import load_context
from app.services.grading import apply_hint_penalty, best_valid_score, build_criteria, decide_status
from app.services.progress import max_reachable_order

router = APIRouter(prefix="/api/v1")
STALE_AFTER_SECONDS = 120
COUNTED = ("passed", "failed", "timeout", "runtime_error")  # infrastructure errors never consume an attempt (when a cap exists)
MAX_SUBMISSIONS_PER_MINUTE = 6  # abuse limit (§6.2): policy stays "unlimited practice attempts"
MAX_IN_FLIGHT = 2


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


def _require_reachable(ctx, segment) -> None:
    if segment["segment_order"] > max_reachable_order(ctx.segments, ctx.checkpoints, ctx.progress):
        raise ApiError(400, "CHECKPOINT_REQUIRED", "Complete earlier required checkpoints first")


def _attempt_number(ctx, exercise_id: str) -> int:
    return 1 + len([s for s in ctx.submissions if s["exercise_id"] == exercise_id])


def _view(sub: dict) -> dict:
    status = sub["status"]
    criteria = sub.get("criteria_results") or []
    return {
        "submission_id": sub["id"], "submission_number": sub["submission_number"], "status": status,
        "score": float(sub["score"]) if sub["score"] is not None else None,
        "raw_score": float(sub["raw_score"]) if sub.get("raw_score") is not None else None,
        "max_score": float(sub.get("max_score") or 100),
        "pass_threshold": float(sub["pass_threshold"]) if sub.get("pass_threshold") is not None else None,
        "hints_used": sub.get("hints_used") or 0,
        "hint_penalty": float(sub.get("hint_penalty") or 0),
        "passed_tests": sub["passed_tests"], "total_tests": sub["total_tests"],
        "execution_ms": sub["execution_ms"], "feedback": sub["safe_feedback"],
        "criteria": criteria,
        "remediation": [{"criterion": c["label"], "text": c["remediation"], "objective": c.get("objective"),
                         "review_segment_id": c.get("review_segment_id"), "review_title": c.get("review_title")}
                        for c in criteria if not c["passed"] and c.get("remediation")],
        "infrastructure_error": status in ("error", "expired", "cancelled"), "created_at": sub["created_at"],
    }


@router.get("/exercises/{exercise_id}")
async def get_exercise(exercise_id: str, user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)):
    ex, ctx, segment = await _exercise_ctx(repo, user.id, path_uuid(exercise_id))
    number = _attempt_number(ctx, ex["id"])
    reveals = await repo.list_hint_reveals(user.id, ex["id"], number)
    hints = ex.get("hints") or []
    draft = await repo.get_draft(user.id, ex["id"])
    version = ctx.lecture.get("content_version")
    draft_stale = bool(draft and draft.get("content_version") is not None and draft["content_version"] != version)
    mine = [s for s in ctx.submissions if s["exercise_id"] == ex["id"]]
    return {
        "id": ex["id"], "title": ex["title"], "instructions": ex["instructions"], "language": ex["language"],
        "starter_code": ex["starter_code"], "practice_mode": ex["practice_mode"],
        "pass_threshold": float(ex["pass_threshold"]), "max_attempts": ex["max_attempts"],
        "hints_total": len(hints), "hint_penalty_percent": float(ex.get("hint_penalty_percent") or 0),
        "hints_revealed": [hints[r["hint_index"]] for r in reveals if r["hint_index"] < len(hints)],
        "best_score": best_valid_score(mine), "attempts_used": len(mine),
        "draft": draft["source_code"] if draft and not draft_stale else None, "draft_stale": draft_stale,
        "content_version": version, "runtime": "Python 3 — practice runs in your browser; official grading runs on the server",
        "objective": ex.get("objective") or "", "constraints": ex.get("constraints") or "",
        "visible_examples": ex.get("visible_examples") or [], "success_criteria": ex.get("success_criteria") or [],
        "hints_policy": (f"Hints are optional. Each one lowers that attempt's score by {float(ex.get('hint_penalty_percent') or 0):g} points; "
                         "it never lowers a score you already earned.") if hints else "No hints are available for this exercise.",
        "unlocked": segment["segment_order"] <= max_reachable_order(ctx.segments, ctx.checkpoints, ctx.progress),
    }


class HintBody(BaseModel):
    hint_index: int = Field(ge=0, le=50)


@router.post("/exercises/{exercise_id}/hints")
async def reveal_hint(exercise_id: str, body: HintBody, request: Request, user: CurrentUser = Depends(current_user),
                      repo: Repository = Depends(get_repository)):
    """Idempotent: revealing hint N is only allowed after hints 0..N-1 for the current attempt."""
    ex, ctx, segment = await _exercise_ctx(repo, user.id, path_uuid(exercise_id))
    _require_reachable(ctx, segment)
    hints = ex.get("hints") or []
    number = _attempt_number(ctx, ex["id"])
    reveals = await repo.list_hint_reveals(user.id, ex["id"], number)
    already = {r["hint_index"] for r in reveals}
    if body.hint_index >= len(hints):
        raise ApiError(409, "NO_MORE_HINTS", "There are no more hints for this exercise")
    if body.hint_index not in already:
        if body.hint_index != len(already):
            raise ApiError(409, "HINT_ORDER", "Reveal hints in order")
        await repo.insert_hint_reveal({"learner_id": user.id, "exercise_id": ex["id"], "hint_index": body.hint_index,
                                       "attempt_number": number})
        await audit.record(repo, request, user.id, "hint.revealed", "exercise", ex["id"],
                           {"exercise_id": ex["id"], "hint_index": body.hint_index})
        already.add(body.hint_index)
    return {"hint_index": body.hint_index, "text": hints[body.hint_index], "hints_revealed": len(already),
            "hints_total": len(hints), "penalty_percent": len(already) * float(ex.get("hint_penalty_percent") or 0)}


class DraftBody(BaseModel):
    source_code: str


@router.put("/exercises/{exercise_id}/draft", status_code=204)
async def save_draft(exercise_id: str, body: DraftBody, user: CurrentUser = Depends(current_user),
                     repo: Repository = Depends(get_repository)):
    ex, ctx, segment = await _exercise_ctx(repo, user.id, path_uuid(exercise_id))
    _require_reachable(ctx, segment)
    if len(body.source_code.encode()) > _max_bytes():
        raise ApiError(422, "VALIDATION_ERROR", details=[{"field": "source_code", "issue": "Too large"}])
    await repo.upsert_draft(user.id, ex["id"], body.source_code, ctx.lecture.get("content_version"))


class SubmissionBody(BaseModel):
    source_code: str
    language: str | None = None
    content_version: int | None = None


async def _run_grading(repo: Repository, grader: Grader, sub: dict, ex: dict, lecture: dict, request_id: str | None) -> None:
    started = datetime.now(UTC).isoformat()
    await repo.update_submission(sub["id"], {"status": "running", "started_at": started})
    tests: list[dict] = []
    section_titles = {x["id"]: x["title"] for x in await repo.list_segments(lecture["id"])}
    try:
        tests = await repo.list_exercise_tests(ex["id"])
        result = await grader.grade(sub["source_code"], tests, float(ex["pass_threshold"]))
    except Exception:  # noqa: BLE001 - never leave a submission stuck, never blame the learner
        result = GradeResult("error", feedback=[{"kind": "infrastructure", "message": "Grading failed to run. Please try again."}])

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
        "correlation_id": request_id, "finished_at": datetime.now(UTC).isoformat()})
    await audit.record(repo, None, sub["learner_id"], "submission.finished", "submission", sub["id"],
                       {"status": status, "score": adjusted, "submission_id": sub["id"]})


@router.post("/exercises/{exercise_id}/submissions", status_code=202)
async def create_submission(exercise_id: str, body: SubmissionBody, request: Request, background: BackgroundTasks,
                            user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository),
                            grader: Grader = Depends(get_grader),
                            idempotency_key_header: str | None = Header(default=None, alias="Idempotency-Key")):
    exercise_id = path_uuid(exercise_id)
    key = idempotency_key(idempotency_key_header)
    ex, ctx, segment = await _exercise_ctx(repo, user.id, exercise_id)
    if len(body.source_code.encode()) > _max_bytes() or not body.source_code.strip():
        raise ApiError(422, "VALIDATION_ERROR", details=[{"field": "source_code", "issue": "Empty or too large"}])
    if body.language is not None and body.language.lower() != ex["language"]:
        raise ApiError(422, "VALIDATION_ERROR", details=[{"field": "language", "issue": f"Only {ex['language']} is supported here"}])

    existing = await repo.find_submission_by_key(user.id, key)
    if existing:
        if existing["exercise_id"] != exercise_id or existing["source_code"] != body.source_code:
            raise ApiError(409, "IDEMPOTENCY_CONFLICT", "Idempotency key reused with a different request")
        return {"submission_id": existing["id"], "status": existing["status"],
                "status_url": f"/api/v1/submissions/{existing['id']}"}

    _require_reachable(ctx, segment)
    if body.content_version is not None and body.content_version != ctx.lecture.get("content_version"):
        raise ApiError(409, "CONTENT_CHANGED", "This exercise was updated. Reload the lecture, then submit again.")
    counted = [s for s in ctx.submissions if s["exercise_id"] == exercise_id and s["status"] in COUNTED]
    if ex["max_attempts"] is not None and len(counted) >= ex["max_attempts"]:
        raise ApiError(409, "ATTEMPTS_EXHAUSTED", "No attempts remaining for this exercise")
    since = (datetime.now(UTC) - timedelta(seconds=60)).isoformat()
    recent, in_flight = await repo.submission_load(user.id, since)
    if in_flight >= MAX_IN_FLIGHT or recent >= MAX_SUBMISSIONS_PER_MINUTE:
        await audit.record(repo, request, user.id, "submission.rate_limited", "exercise", exercise_id,
                           {"exercise_id": exercise_id, "count": recent})
        raise ApiError(429, "RATE_LIMITED", "You're submitting very quickly. Wait a few seconds, then try again.")

    sub = await repo.insert_submission({
        "learner_id": user.id, "exercise_id": exercise_id, "source_code": body.source_code,
        "idempotency_key": key, "status": "queued", "content_version": ctx.lecture.get("content_version"),
        "snapshot_sha256": hashlib.sha256(body.source_code.encode()).hexdigest(),
        "test_suite_version": ex.get("test_suite_version"), "pass_threshold": ex["pass_threshold"],
        "correlation_id": getattr(request.state, "request_id", None)})
    await audit.record(repo, request, user.id, "submission.created", "submission", sub["id"],
                       {"submission_id": sub["id"], "exercise_id": exercise_id})
    background.add_task(_run_grading, repo, grader, sub, ex, ctx.lecture, getattr(request.state, "request_id", None))
    return {"submission_id": sub["id"], "status": "queued", "status_url": f"/api/v1/submissions/{sub['id']}"}


@router.get("/submissions/{submission_id}")
async def get_submission(submission_id: str, user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)):
    sub = await repo.get_submission(path_uuid(submission_id))
    if not sub or not await can_view_learner(user, sub["learner_id"], repo):
        raise ApiError(404, "NOT_FOUND")  # not-found, not 403, so ids can't be probed
    if sub["status"] in ("queued", "running"):
        created = datetime.fromisoformat(str(sub["created_at"]).replace("Z", "+00:00"))
        if (datetime.now(UTC) - created).total_seconds() > STALE_AFTER_SECONDS:
            sub = await repo.update_submission(sub["id"], {"status": "expired", "safe_feedback": [
                {"kind": "infrastructure", "message": "Grading took too long and was stopped. Your code was not judged and your score is unchanged. Please submit again."}]}) or sub
    return _view(sub)


@router.get("/exercises/{exercise_id}/submissions")
async def list_my_submissions(exercise_id: str, user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)):
    subs = await repo.list_submissions(user.id, [path_uuid(exercise_id)])
    return {"submissions": [_view(s) for s in subs], "best_score": best_valid_score(subs)}


async def can_view_learner(user: CurrentUser, learner_id: str, repo: Repository) -> bool:
    """Owner always; admin any; teacher only for currently assigned learners (revocable)."""
    if learner_id == user.id or user.role == "admin":
        return True
    if user.role == "teacher":
        return learner_id in await repo.list_assigned_learner_ids(user.id)
    return False
