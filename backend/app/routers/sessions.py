from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth import CurrentUser, current_user
from app.errors import ApiError
from app.repository import Repository, get_repository
from app.routers.deps import path_uuid
from app.services.context import LectureContext, load_context
from app.services.progress import max_reachable_order, missing_gates

router = APIRouter(prefix="/api/v1")


def _explanation(ctx: LectureContext, attempt: dict) -> str:
    q = ctx.questions.get(attempt["question_id"], {})
    if attempt["is_correct"]:
        return q.get("explanation_correct", "")
    return q.get("explanation_incorrect") or q.get("explanation_correct", "")


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


async def get_or_create(repo: Repository, user_id: str, ctx: LectureContext) -> dict:
    session = await repo.get_session(user_id, ctx.lecture["id"])
    if not session:
        first = ctx.segments[0]["id"] if ctx.segments else None
        session = await repo.create_session(user_id, ctx.lecture["id"], first)
    return session


@router.get("/lectures/{lecture_id}/session")
async def get_session(lecture_id: str, user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)):
    ctx = await load_context(repo, user.id, path_uuid(lecture_id))
    session = await get_or_create(repo, user.id, ctx)
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
async def complete_lecture(lecture_id: str, _: CompleteBody | None = None, user: CurrentUser = Depends(current_user),
                           repo: Repository = Depends(get_repository)):
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
    return session_view(ctx, session) | {"completed_at": session.get("completed_at")}
