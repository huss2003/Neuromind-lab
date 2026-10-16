"""Practical Labs section: course -> months -> each lecture's lab with its server-decided state."""
from fastapi import APIRouter, Depends

from app.auth import CurrentUser, current_user
from app.repository import Repository, get_repository
from app.services import labs
from app.services.dashboard import lecture_states

router = APIRouter(prefix="/api/v1")


@router.get("/labs")
async def list_labs(user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)):
    courses = await repo.list_published_courses()
    if user.role == "learner":
        enrolled = set(await repo.list_enrolled_course_ids(user.id))
        courses = [c for c in courses if c["id"] in enrolled]
    subs_all = await repo.list_learner_submissions(user.id) if user.role == "learner" else []
    by_exercise: dict[str, list] = {}
    for s in sorted(subs_all, key=lambda x: x["created_at"]):
        by_exercise.setdefault(s["exercise_id"], []).append(s)
    out = []
    for c in courses:
        lectures = await repo.list_published_lectures(c["id"])
        states = await lecture_states(repo, user.id, lectures) if user.role == "learner" else {}
        exercises = await repo.list_published_exercises([lec["id"] for lec in lectures])
        ex_by_lecture: dict[str, dict] = {}
        for ex in exercises:
            ex_by_lecture.setdefault(ex["lecture_id"], ex)  # one lab per lecture
        modules = await repo.list_published_modules(c["id"])
        rows = []
        for lec in lectures:
            ex = ex_by_lecture.get(lec["id"])
            if not ex:
                continue
            lstate = states.get(lec["id"], "available")
            subs = by_exercise.get(ex["id"], [])
            rows.append({"lecture_id": lec["id"], "lecture_number": lec["lecture_number"], "lecture_title": lec["title"], "module_id": lec.get("module_id"),
                         "exercise_id": ex["id"], "title": ex["title"], "lab_kind": ex.get("lab_kind") or "code", "packages": ex.get("packages") or [],
                         "state": labs.lab_state(lstate, subs), "lecture_state": lstate, "attempts": len(subs),
                         "last_status": subs[-1]["status"] if subs else None})
        grouped = [{"id": m["id"], "module_number": m["module_number"], "title": m["title"], "labs": [r for r in rows if r["module_id"] == m["id"]]} for m in modules]
        orphans = [r for r in rows if not any(r["module_id"] == m["id"] for m in modules)]
        if orphans:
            grouped.append({"id": "other", "module_number": len(modules) + 1, "title": "Other lectures", "labs": orphans})
        out.append({"id": c["id"], "title": c["title"], "description": c.get("description", ""), "modules": grouped,
                    "total": len(rows), "passed": sum(1 for r in rows if r["state"] == "passed")})
    return {"courses": out}
