from fastapi import APIRouter, Depends

from app.auth import CurrentUser, require_roles
from app.errors import ApiError
from app.repository import Repository, get_repository
from app.routers.deps import path_uuid

router = APIRouter(prefix="/api/v1/teacher")
guard = require_roles("teacher", "admin")


@router.get("/learners")
async def learners(_: CurrentUser = Depends(guard), repo: Repository = Depends(get_repository)):
    return {"learners": await repo.list_learners()}


@router.get("/learners/{learner_id}/results")
async def learner_results(learner_id: str, _: CurrentUser = Depends(guard), repo: Repository = Depends(get_repository)):
    learner_id = path_uuid(learner_id)
    profile = await repo.get_profile(learner_id)
    if not profile:
        raise ApiError(404, "NOT_FOUND")
    sessions = await repo.list_learner_sessions(learner_id)
    attempts = await repo.list_learner_attempts(learner_id)
    submissions = await repo.list_learner_submissions(learner_id)
    return {
        "learner": {"id": profile["id"], "display_name": profile["display_name"]},
        "sessions": [{"lecture_id": s["lecture_id"], "status": s["status"], "completed_at": s["completed_at"],
                      "last_seen_at": s["last_seen_at"]} for s in sessions],
        "checkpoint_attempts": [{"checkpoint_id": a["checkpoint_id"], "is_correct": a["is_correct"],
                                 "score": float(a["score"]), "submitted_at": a["submitted_at"]} for a in attempts],
        "submissions": [{"submission_id": s["id"], "exercise_id": s["exercise_id"], "number": s["submission_number"],
                         "status": s["status"], "score": float(s["score"]) if s["score"] is not None else None,
                         "passed_tests": s["passed_tests"], "total_tests": s["total_tests"],
                         "created_at": s["created_at"]} for s in submissions],
    }
