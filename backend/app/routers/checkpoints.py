from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel

from app.auth import CurrentUser, current_user
from app.errors import ApiError
from app.repository import Repository, get_repository
from app.routers.deps import idempotency_key, path_uuid
from app.services.context import load_context
from app.services.progress import attempt_meets_threshold, max_reachable_order

router = APIRouter(prefix="/api/v1")


class AttemptBody(BaseModel):
    question_id: str
    selected_option_id: str


def _response(attempt: dict, q: dict, completed: bool) -> dict:
    explanation = q["explanation_correct"] if attempt["is_correct"] else (q.get("explanation_incorrect") or q["explanation_correct"])
    return {"attempt_id": attempt["id"], "is_correct": attempt["is_correct"], "score": float(attempt["score"]),
            "explanation": explanation, "checkpoint_completed": completed,
            "next_action": {"type": "next_segment"} if completed else {"type": "retry"}}


@router.post("/checkpoints/{checkpoint_id}/attempts")
async def submit_attempt(checkpoint_id: str, body: AttemptBody, user: CurrentUser = Depends(current_user),
                         repo: Repository = Depends(get_repository),
                         idempotency_key_header: str | None = Header(default=None, alias="Idempotency-Key")):
    checkpoint_id = path_uuid(checkpoint_id)
    key = idempotency_key(idempotency_key_header)
    cp = await repo.get_checkpoint(checkpoint_id)
    if not cp:
        raise ApiError(404, "NOT_FOUND")
    ctx = await load_context(repo, user.id, cp["lecture_id"])  # 404 if lecture unpublished
    q = ctx.questions.get(cp["question_id"])
    segment = next((s for s in ctx.segments if s.get("checkpoint_id") == checkpoint_id), None)
    if not q or not segment:
        raise ApiError(404, "NOT_FOUND")
    if body.question_id != cp["question_id"]:
        raise ApiError(422, "VALIDATION_ERROR", details=[{"field": "question_id", "issue": "Does not belong to checkpoint"}])
    if body.selected_option_id not in {o["id"] for o in q["options"]}:
        raise ApiError(422, "VALIDATION_ERROR", details=[{"field": "option_id", "issue": "Unknown option"}])

    existing = await repo.find_attempt_by_key(user.id, key)
    if existing:  # idempotent replay
        if existing["checkpoint_id"] != checkpoint_id or existing["selected_option_id"] != body.selected_option_id:
            raise ApiError(409, "IDEMPOTENCY_CONFLICT", "Idempotency key reused with a different request")
        return _response(existing, q, checkpoint_id in ctx.progress.completed_checkpoint_ids)

    if segment["segment_order"] > max_reachable_order(ctx.segments, ctx.checkpoints, ctx.progress):
        raise ApiError(400, "CHECKPOINT_REQUIRED", "An earlier required checkpoint must be completed first")

    points = float(q["points"])
    is_correct = body.selected_option_id == q["correct_option_id"]  # never taken from the client
    attempt = await repo.insert_attempt({
        "learner_id": user.id, "checkpoint_id": checkpoint_id, "question_id": q["id"],
        "selected_option_id": body.selected_option_id, "is_correct": is_correct,
        "score": points if is_correct else 0, "idempotency_key": key})
    completed = checkpoint_id in ctx.progress.completed_checkpoint_ids or attempt_meets_threshold(attempt, cp, points)
    return _response(attempt, q, completed)


@router.get("/checkpoints/{checkpoint_id}/attempts")
async def list_attempts(checkpoint_id: str, user: CurrentUser = Depends(current_user),
                        repo: Repository = Depends(get_repository)):
    checkpoint_id = path_uuid(checkpoint_id)
    attempts = await repo.list_attempts(user.id, [checkpoint_id])  # own attempts only
    return {"attempts": [{"attempt_id": a["id"], "is_correct": a["is_correct"], "score": float(a["score"]),
                          "submitted_at": a["submitted_at"]} for a in attempts]}
