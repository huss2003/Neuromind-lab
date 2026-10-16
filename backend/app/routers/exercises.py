import asyncio
import hashlib
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Request
from pydantic import BaseModel, Field

from app.auth import CurrentUser, current_user
from app.errors import ApiError
from app.grader_client import GradeResult, Grader, get_grader
from app.repository import Repository, get_repository
from app.routers.deps import idempotency_key, path_uuid
from app.services import audit, labs
from app.services.context import load_context
from app.services.finalize import finalize_submission
from app.services.grading import best_valid_score
from app.services.progress import max_reachable_order

router = APIRouter(prefix="/api/v1")
STALE_AFTER_SECONDS = 120  # inline mode; queue mode uses QUEUE_STALE_SECONDS (leases and retries need longer)
COUNTED = ("passed", "failed", "timeout", "runtime_error")  # infrastructure errors never consume an attempt (when a cap exists)
MAX_SUBMISSIONS_PER_MINUTE = 6  # abuse limit (§6.2): policy stays "unlimited practice attempts"
MAX_IN_FLIGHT = 2


def grading_mode() -> str:
    """`inline` (default, local dev: API calls the grader) or `queue` (hosted: a private worker pulls jobs)."""
    return "queue" if os.getenv("GRADER_MODE", "inline").lower() == "queue" else "inline"


def _stale_after() -> int:
    return int(os.getenv("QUEUE_STALE_SECONDS", "900")) if grading_mode() == "queue" else STALE_AFTER_SECONDS


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
        "content_version": sub.get("content_version"), "test_suite_version": sub.get("test_suite_version"),
        "started_at": sub.get("started_at"), "finished_at": sub.get("finished_at"),
        "awaiting_review": status == "submitted",
        "quiz_results": (sub.get("answers") or {}).get("results") if isinstance(sub.get("answers"), dict) else None,
        "answers": {k: v for k, v in (sub.get("answers") or {}).items() if k in ("link", "notes", "checklist")} if isinstance(sub.get("answers"), dict) else None,
        "review": sub.get("_review"),
    }


@router.get("/exercises/{exercise_id}")
async def get_exercise(exercise_id: str, user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)):
    ex, ctx, segment = await _exercise_ctx(repo, user.id, path_uuid(exercise_id))
    number = _attempt_number(ctx, ex["id"])
    cycle, redo_count = await labs.hint_cycle(repo, user.id, ex)
    reveals = await labs.hints_revealed(repo, user.id, ex, number, cycle)
    hints = ex.get("hints") or []
    draft = await repo.get_draft(user.id, ex["id"])
    kind = ex.get("lab_kind") or "code"
    pass_fail = labs.is_pass_fail(ex)
    tests = await repo.list_exercise_tests(ex["id"]) if kind == "code" else []
    questions = [{"id": q["id"], "question_order": q["question_order"], "prompt": q["prompt"], "options": q["options"]}
                 for q in await repo.list_lab_questions(ex["id"])] if kind == "quiz" else []
    last = next((x for x in reversed([s for s in ctx.submissions if s["exercise_id"] == ex["id"]])), None)
    review = await repo.get_review(last["id"]) if last and kind in labs.REVIEWED_KINDS and last["status"] in ("passed", "failed") else None
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
        "hints_policy": ("No hints are available for this exercise." if not hints else
                         f"You can take up to {labs.hints_max(ex)} hints for this lab. After the last hint you can start the lab again (Redo)." if pass_fail else
                         f"Hints are optional. Each one lowers that attempt's score by {float(ex.get('hint_penalty_percent') or 0):g} points; "
                         "it never lowers a score you already earned."),
        "unlocked": segment["segment_order"] <= max_reachable_order(ctx.segments, ctx.checkpoints, ctx.progress),
        # practical labs
        "lab_kind": kind, "scoring": "pass_fail" if pass_fail else "score",
        "packages": ex.get("packages") or [], "assets": labs.public_assets(ex.get("assets") or []), "limits": labs.limits_for(ex),
        "visible_checks": labs.visible_checks(tests), "hints_max": labs.hints_max(ex), "hints_used": len(reveals),
        "cycle": cycle, "redo_count": redo_count, "redo_available": pass_fail and bool(hints) and len(reveals) >= labs.hints_max(ex),
        "questions": questions, "rubric": ex.get("rubric") or [], "checklist": ex.get("checklist") or [],
        "lecture": {"id": ctx.lecture["id"], "lecture_number": ctx.lecture.get("lecture_number"), "title": ctx.lecture.get("title")},
        "review": {"passed": review["passed"], "feedback": review["feedback"], "scores": review.get("scores") or [], "reviewed_at": review.get("updated_at") or review.get("created_at")} if review else None,
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
    cycle, _redo = await labs.hint_cycle(repo, user.id, ex)
    reveals = await labs.hints_revealed(repo, user.id, ex, number, cycle)
    already = {r["hint_index"] for r in reveals}
    if body.hint_index >= len(hints):
        raise ApiError(409, "NO_MORE_HINTS", "There are no more hints for this exercise")
    if body.hint_index not in already:
        if body.hint_index != len(already):
            raise ApiError(409, "HINT_ORDER", "Reveal hints in order")
        if labs.is_pass_fail(ex) and len(already) >= labs.hints_max(ex):
            raise ApiError(409, "HINTS_EXHAUSTED", f"You have used all {labs.hints_max(ex)} hints for this lab. Start again with Redo to get fresh hints.")
        await repo.insert_hint_reveal({"learner_id": user.id, "exercise_id": ex["id"], "hint_index": body.hint_index,
                                       "attempt_number": number, "cycle": cycle})
        await audit.record(repo, request, user.id, "hint.revealed", "exercise", ex["id"],
                           {"exercise_id": ex["id"], "hint_index": body.hint_index})
        already.add(body.hint_index)
    return {"hint_index": body.hint_index, "text": hints[body.hint_index], "hints_revealed": len(already),
            "hints_total": len(hints), "penalty_percent": len(already) * float(ex.get("hint_penalty_percent") or 0)}


@router.post("/exercises/{exercise_id}/redo")
async def redo_lab(exercise_id: str, request: Request, user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)):
    """Start the lab again after the hints are used up: fresh hints and starter code; the attempt history is kept."""
    ex, ctx, segment = await _exercise_ctx(repo, user.id, path_uuid(exercise_id))
    _require_reachable(ctx, segment)
    if not labs.is_pass_fail(ex):
        raise ApiError(409, "REDO_NOT_AVAILABLE", "This exercise does not use Redo")
    cycle, redo_count = await labs.hint_cycle(repo, user.id, ex)
    reveals = await labs.hints_revealed(repo, user.id, ex, _attempt_number(ctx, ex["id"]), cycle)
    if len(reveals) < labs.hints_max(ex):
        raise ApiError(409, "REDO_NOT_AVAILABLE", "Redo becomes available once you have used all the hints for this lab")
    await repo.upsert_hint_state(user.id, ex["id"], cycle + 1, redo_count + 1)
    await repo.delete_draft(user.id, ex["id"])
    await audit.record(repo, request, user.id, "lab.redo", "exercise", ex["id"], {"exercise_id": ex["id"], "count": redo_count + 1})
    return {"cycle": cycle + 1, "redo_count": redo_count + 1, "hints_used": 0, "hints_max": labs.hints_max(ex), "starter_code": ex["starter_code"]}


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
    source_code: str = ""
    language: str | None = None
    content_version: int | None = None
    answers: dict[str, Any] | None = None  # quiz: {question_id: option_id}; upload: {link, notes, checklist}


async def _run_grading(repo: Repository, grader: Grader, sub: dict, ex: dict, lecture: dict, request_id: str | None) -> None:
    """Inline mode (local development): grade in-process-adjacent and finalise. Queue mode uses routers/worker.py."""
    await repo.update_submission(sub["id"], {"status": "running", "started_at": datetime.now(UTC).isoformat()})
    tests: list[dict] = []
    try:
        tests = await repo.list_exercise_tests(ex["id"])
        result = await grader.grade(sub["source_code"], tests, float(ex["pass_threshold"]))
    except Exception:  # noqa: BLE001 - never leave a submission stuck, never blame the learner
        result = GradeResult("error", feedback=[{"kind": "infrastructure", "message": "Grading failed to run. Please try again."}])
    await finalize_submission(repo, sub, ex, lecture, result, tests, request_id)


@router.post("/exercises/{exercise_id}/submissions", status_code=202)
async def create_submission(exercise_id: str, body: SubmissionBody, request: Request, background: BackgroundTasks,
                            user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository),
                            grader: Grader = Depends(get_grader),
                            idempotency_key_header: str | None = Header(default=None, alias="Idempotency-Key")):
    exercise_id = path_uuid(exercise_id)
    key = idempotency_key(idempotency_key_header)
    since = (datetime.now(UTC) - timedelta(seconds=60)).isoformat()
    # The context, the idempotency lookup and the rate-limit counters are independent reads: fetch them together.
    ctx_result, existing_result, load_result = await asyncio.gather(
        _exercise_ctx(repo, user.id, exercise_id), repo.find_submission_by_key(user.id, key),
        repo.submission_load(user.id, since), return_exceptions=True)
    if isinstance(ctx_result, BaseException):
        raise ctx_result
    ex, ctx, segment = ctx_result
    kind = ex.get("lab_kind") or "code"
    if len(body.source_code.encode()) > _max_bytes():
        raise ApiError(422, "VALIDATION_ERROR", details=[{"field": "source_code", "issue": "Too large"}])
    if kind in ("code", "written") and not body.source_code.strip():
        raise ApiError(422, "VALIDATION_ERROR", details=[{"field": "source_code", "issue": "Nothing to submit yet" if kind == "written" else "Empty or too large"}])
    if kind == "code" and body.language is not None and body.language.lower() != ex["language"]:
        raise ApiError(422, "VALIDATION_ERROR", details=[{"field": "language", "issue": f"Only {ex['language']} is supported here"}])
    if kind == "written" and len(body.source_code) > labs.MAX_TEXT_CHARS:
        raise ApiError(422, "VALIDATION_ERROR", details=[{"field": "source_code", "issue": f"Answers are limited to {labs.MAX_TEXT_CHARS} characters"}])
    if kind == "quiz" and (not isinstance(body.answers, dict) or not body.answers):
        raise ApiError(422, "VALIDATION_ERROR", details=[{"field": "answers", "issue": "Answer the questions first"}])
    if kind == "upload":
        problems = labs.validate_upload(body.answers or {}, ex.get("checklist") or [])
        if problems:
            raise ApiError(422, "VALIDATION_ERROR", details=problems)

    if isinstance(existing_result, BaseException):
        raise existing_result
    existing = existing_result
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
    if isinstance(load_result, BaseException):
        raise load_result
    recent, in_flight = load_result
    if in_flight >= MAX_IN_FLIGHT or recent >= MAX_SUBMISSIONS_PER_MINUTE:
        await audit.record(repo, request, user.id, "submission.rate_limited", "exercise", exercise_id,
                           {"exercise_id": exercise_id, "count": recent})
        raise ApiError(429, "RATE_LIMITED", "You're submitting very quickly. Wait a few seconds, then try again.")

    row: dict[str, Any] = {
        "learner_id": user.id, "exercise_id": exercise_id, "source_code": body.source_code,
        "idempotency_key": key, "status": "queued", "content_version": ctx.lecture.get("content_version"),
        "snapshot_sha256": hashlib.sha256(body.source_code.encode()).hexdigest(),
        "test_suite_version": ex.get("test_suite_version"), "pass_threshold": ex["pass_threshold"],
        "correlation_id": getattr(request.state, "request_id", None)}
    if kind == "quiz":  # marked here and now; never trusts the client for correctness
        questions = await repo.list_lab_questions(ex["id"])
        marked = labs.mark_quiz(questions, {str(k): str(v) for k, v in (body.answers or {}).items()})
        row.update({"status": "passed" if marked["passed"] else "failed", "score": marked["score"], "raw_score": marked["score"],
                    "passed_tests": marked["correct"], "total_tests": marked["total"], "finished_at": datetime.now(UTC).isoformat(),
                    "answers": {"responses": body.answers, "results": marked["results"]}, "max_score": 100,
                    "criteria_results": [{"label": f"Question {r['question_order']}", "hidden": False, "passed": r["correct"], "remediation": None if r["correct"] else (r["explanation"] or None)} for r in marked["results"]],
                    "safe_feedback": [{"kind": "success" if marked["passed"] else "failure",
                                       "message": f"{marked['correct']} of {marked['total']} answers correct." + ("" if marked["passed"] else " Review the explanations and try again.")}]})
    elif kind in labs.REVIEWED_KINDS:
        row.update({"status": "submitted", "answers": body.answers if kind == "upload" else {"kind": "written"},
                    "safe_feedback": [{"kind": "info", "message": "Sent to your teacher for review."}]})
    sub = await repo.insert_submission(row)
    background.add_task(audit.record, repo, request, user.id, "submission.created", "submission", sub["id"],
                        {"submission_id": sub["id"], "exercise_id": exercise_id})  # best-effort; off the request path
    if kind == "quiz":
        background.add_task(audit.record, repo, None, user.id, "submission.finished", "submission", sub["id"], {"status": sub["status"], "score": sub.get("score"), "submission_id": sub["id"]})
    elif kind == "code" and grading_mode() == "inline":  # queue mode: a private worker claims the job from the database
        background.add_task(_run_grading, repo, grader, sub, ex, ctx.lecture, getattr(request.state, "request_id", None))
    return {"submission_id": sub["id"], "status": sub["status"], "status_url": f"/api/v1/submissions/{sub['id']}"}


@router.get("/submissions/{submission_id}")
async def get_submission(submission_id: str, user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)):
    sub = await repo.get_submission(path_uuid(submission_id))
    if not sub or not await can_view_learner(user, sub["learner_id"], repo):
        raise ApiError(404, "NOT_FOUND")  # not-found, not 403, so ids can't be probed
    if sub["status"] in ("queued", "running"):
        created = datetime.fromisoformat(str(sub["created_at"]).replace("Z", "+00:00"))
        if (datetime.now(UTC) - created).total_seconds() > _stale_after():
            sub = await repo.update_submission(sub["id"], {"status": "expired", "safe_feedback": [
                {"kind": "infrastructure", "message": "Grading took too long and was stopped. Your code was not judged and your score is unchanged. Please submit again."}]}) or sub
    if sub["status"] in ("passed", "failed") and sub.get("answers") is not None or sub["status"] == "submitted":
        review = await repo.get_review(sub["id"])
        if review:
            sub = {**sub, "_review": {"passed": review["passed"], "feedback": review["feedback"], "scores": review.get("scores") or [],
                                      "reviewed_at": review.get("updated_at") or review.get("created_at")}}
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
