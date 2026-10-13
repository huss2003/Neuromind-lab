from fastapi import APIRouter, Depends

from app.auth import CurrentUser, current_user
from app.repository import Repository, get_repository
from app.services.dashboard import lecture_states, recent_attempts, remediation_queue

router = APIRouter(prefix="/api/v1")


@router.get("/me/dashboard")
async def my_dashboard(user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)):
    """Everything on the learner dashboard is derived from persisted records scoped to the caller (§12)."""
    enrolled = set(await repo.list_enrolled_course_ids(user.id))
    courses = [c for c in await repo.list_published_courses() if c["id"] in enrolled]
    if not courses:
        return {"enrolled": False, "course": None, "continue": None, "recent_attempts": [], "remediation_queue": []}
    course = courses[0]
    lectures = await repo.list_published_lectures(course["id"])
    states = await lecture_states(repo, user.id, lectures)
    nxt = next((x for x in lectures if states[x["id"]] in ("in_progress", "needs_attention")), None) \
        or next((x for x in lectures if states[x["id"]] == "available"), None)
    return {
        "enrolled": True,
        "course": {"id": course["id"], "title": course["title"], "description": course["description"],
                   "completed_lectures": sum(1 for v in states.values() if v == "completed"), "total_lectures": len(lectures)},
        "continue": {"lecture_id": nxt["id"], "lecture_number": nxt["lecture_number"], "title": nxt["title"],
                     "state": states[nxt["id"]]} if nxt else None,
        "recent_attempts": await recent_attempts(repo, user.id),
        "remediation_queue": await remediation_queue(repo, user.id),
    }
