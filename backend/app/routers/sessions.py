from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.auth import CurrentUser, current_user
from app.errors import ApiError
from app.repository import Repository, get_repository
from app.routers.deps import path_uuid
from app.services import certificates
from app.services.context import LectureContext, load_context
from app.services.grading import best_valid_score, explanation_for
from app.services.audit import record as audit_record
from app.services.progress import max_reachable_order, missing_gates

router = APIRouter(prefix="/api/v1")


def _explanation(ctx: LectureContext, attempt: dict) -> str:
    return explanation_for(ctx.questions.get(attempt["question_id"], {}), attempt["is_correct"])


def session_view(ctx: LectureContext, session: dict) -> dict:
    latest: dict[str, dict] = {}
    for a in ctx.attempts:  # ordered oldest -> newest
        latest[a["checkpoint_id"]] = a
    results = {
        cid: {"attempt_id": a["id"], "is_correct": a["is_correct"], "score": float(a["score"]),
              "explanation": _explanation(ctx, a), "checkpoint_completed": cid in ctx.progress.completed_checkpoint_ids}
        for cid, a in latest.items()
    }
    return {
        "lecture_state": lecture_state(ctx, session),
        "progress": progress_breakdown(ctx, session),
        "lecture_id": session["lecture_id"],
        "current_segment_id": session["current_segment_id"],
        "playback_position_seconds": session["playback_position_seconds"],
        "status": session["status"],
        "completed_checkpoint_ids": sorted(ctx.progress.completed_checkpoint_ids),
        "completed_exercise_ids": sorted(ctx.progress.completed_exercise_ids),
        "checkpoint_results": results,
        "max_reachable_order": max_reachable_order(ctx.segments, ctx.checkpoints, ctx.progress),
        "state_version": session["state_version"],
    }


def lecture_state(ctx: LectureContext, session: dict) -> str:
    """Central, server-side state vocabulary from the flow spec (§7)."""
    if session["status"] == "completed":
        return "COMPLETED"
    subs = [x for x in ctx.submissions]
    if any(x["status"] in ("queued", "running") for x in subs):
        return "GRADING_PENDING"
    passed = {x["exercise_id"] for x in subs if x["status"] == "passed"}
    if any(x["status"] in ("failed", "runtime_error") and x["exercise_id"] not in passed for x in subs):
        return "REMEDIATION_REQUIRED"
    first = ctx.segments[0]["id"] if ctx.segments else None
    untouched = not ctx.attempts and not subs and session.get("current_segment_id") == first and not session.get("playback_position_seconds")
    return "NOT_STARTED" if untouched else "IN_PROGRESS"


def progress_breakdown(ctx: LectureContext, session: dict) -> dict:
    """§4.4: media, checkpoint, lab progress and mastery are reported separately."""
    done_all = session["status"] == "completed"
    cur = next((x for x in ctx.segments if x["id"] == session.get("current_segment_id")), None)
    cur_order = cur["segment_order"] if cur else 0
    videos = [x for x in ctx.segments if x["segment_type"] == "video"]
    cps = [x for x in ctx.segments if x["segment_type"] in ("checkpoint", "exit_check")]
    labs = [x for x in ctx.segments if x["segment_type"] == "exercise"]
    ex_ids = [x["exercise_id"] for x in labs if x.get("exercise_id")]
    subs = [x for x in ctx.submissions if x["exercise_id"] in ex_ids]
    thresholds = [float(ctx.exercises[e]["pass_threshold"]) for e in ex_ids if e in ctx.exercises]
    return {
        "media": {"done": sum(1 for v in videos if done_all or v["segment_order"] < cur_order), "total": len(videos)},
        "checkpoints": {"done": sum(1 for c in cps if c.get("checkpoint_id") in ctx.progress.completed_checkpoint_ids), "total": len(cps)},
        "labs": {"done": sum(1 for x in labs if x.get("exercise_id") in ctx.progress.completed_exercise_ids), "total": len(labs)},
        "mastery": {"best_exercise_score": best_valid_score(subs), "pass_mark": min(thresholds) if thresholds else None,
                    "lecture_completed": done_all},
    }


async def get_or_create(repo: Repository, user_id: str, ctx: LectureContext, request: Request | None = None) -> dict:
    session = await repo.get_session(user_id, ctx.lecture["id"])
    if not session:
        first = ctx.segments[0]["id"] if ctx.segments else None
        session = await repo.create_session(user_id, ctx.lecture["id"], first)
        await audit_record(repo, request, user_id, "lecture.opened", "lecture", ctx.lecture["id"],
                           {"lecture_id": ctx.lecture["id"]})
    return session


@router.get("/lectures/{lecture_id}/session")
async def get_session(lecture_id: str, request: Request, user: CurrentUser = Depends(current_user),
                      repo: Repository = Depends(get_repository)):
    ctx = await load_context(repo, user.id, path_uuid(lecture_id))
    session = await get_or_create(repo, user.id, ctx, request)
    return session_view(ctx, session)


class SessionPatch(BaseModel):
    current_segment_id: str
    playback_position_seconds: int = Field(ge=0, le=86400)
    state_version: int = Field(ge=1)


@router.patch("/lectures/{lecture_id}/session")
async def patch_session(lecture_id: str, body: SessionPatch, user: CurrentUser = Depends(current_user),
                        repo: Repository = Depends(get_repository)):
    ctx = await load_context(repo, user.id, path_uuid(lecture_id))
    session = await get_or_create(repo, user.id, ctx)
    target = next((s for s in ctx.segments if s["id"] == body.current_segment_id), None)
    if not target:
        raise ApiError(422, "VALIDATION_ERROR", details=[{"field": "current_segment_id", "issue": "Not in this lecture"}])
    if target["segment_order"] > max_reachable_order(ctx.segments, ctx.checkpoints, ctx.progress):
        raise ApiError(400, "CHECKPOINT_REQUIRED", "A required checkpoint must be completed first")
    updated = await repo.update_session(session["id"], body.state_version, {
        "current_segment_id": target["id"], "playback_position_seconds": body.playback_position_seconds,
        "last_seen_at": datetime.now(UTC).isoformat()})
    if not updated:
        raise ApiError(409, "STALE_STATE", "Lecture state changed elsewhere; reload and try again")
    return session_view(ctx, updated)


class CompleteBody(BaseModel):
    exit_check_completed: bool = False  # advisory only; server decides


@router.post("/lectures/{lecture_id}/complete")
async def complete_lecture(lecture_id: str, request: Request, _: CompleteBody | None = None,
                           user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)):
    ctx = await load_context(repo, user.id, path_uuid(lecture_id))
    session = await get_or_create(repo, user.id, ctx)
    gaps = missing_gates(ctx.segments, ctx.checkpoints, ctx.progress)
    if gaps:
        raise ApiError(400, "REQUIREMENTS_NOT_MET", "Required steps are not complete",
                       [{"field": g["id"], "issue": f"Incomplete: {g['title']}"} for g in gaps])
    if session["status"] != "completed":
        session = await repo.update_session(session["id"], None, {
            "status": "completed", "completed_at": datetime.now(UTC).isoformat()}) or session
        await repo.recompute_progress(user.id, ctx.lecture["course_id"])
        await audit_record(repo, request, user.id, "lecture.completed", "lecture", ctx.lecture["id"])
        cert, created = await certificates.issue_if_eligible(repo, user.id, ctx.lecture["course_id"])
        if cert and created:
            await audit_record(repo, request, user.id, "certificate.issued", "certificate", cert["id"], {"serial": cert["serial"]})
    return session_view(ctx, session) | {"completed_at": session.get("completed_at")}


@router.get("/me/progress")
async def my_progress(user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)):
    """Lecture status list for the dashboard (additive endpoint, see API_SPEC)."""
    sessions = await repo.list_learner_sessions(user.id)
    return {"sessions": [{"lecture_id": s["lecture_id"], "status": s["status"],
                          "current_segment_id": s["current_segment_id"], "completed_at": s["completed_at"]} for s in sessions]}


@router.get("/me/feedback")
async def my_feedback(user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)):
    """Only the learner's own, published teacher feedback."""
    rows = await repo.list_feedback(user.id, published_only=True)
    return {"feedback": [{"id": r["id"], "body": r["body"], "created_at": r["created_at"],
                          "submission_id": r.get("submission_id")} for r in rows]}
