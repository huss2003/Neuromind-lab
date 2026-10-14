from fastapi import APIRouter, Depends

from app.auth import CurrentUser, current_user
from app.errors import ApiError
from app.repository import Repository, get_repository
from app.routers.deps import path_uuid as _uuid
from app.services.audit import record as audit_record  # noqa: F401  (kept for symmetry with other routers)
from app.services.context import ensure_available, ensure_enrolled
from app.services.dashboard import lecture_states
from app.services.manifest import LectureManifest, ManifestError, Prereq, build_segment

router = APIRouter(prefix="/api/v1")

ATTEMPT_POLICY = ("You can practise as often as you like. Practice runs in your browser and never counts. "
                  "Each official submission is saved, and your best valid score is kept.")


@router.get("/courses")
async def list_courses(user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)):
    """Learners see only courses they are enrolled in; teachers and admins see every published course."""
    courses = await repo.list_published_courses()
    if user.role == "learner":
        enrolled = set(await repo.list_enrolled_course_ids(user.id))
        courses = [c for c in courses if c["id"] in enrolled]
    return {"courses": courses}


@router.get("/courses/{course_id}")
async def get_course(course_id: str, user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)):
    course = await repo.get_published_course(_uuid(course_id))
    if not course:
        raise ApiError(404, "NOT_FOUND")
    if user.role == "learner":
        await ensure_enrolled(repo, user.id, course["id"])
    lectures = await repo.list_published_lectures(course["id"])
    states = await lecture_states(repo, user.id, lectures)
    lectures = [{**lec, "state": states.get(lec["id"], "available")} for lec in lectures]
    modules = await repo.list_published_modules(course["id"])
    grouped = [{**m, "lectures": [x for x in lectures if x.get("module_id") == m["id"]]} for m in modules]
    return {**course, "lectures": lectures, "modules": grouped}


def _criteria(segments: list[dict], exercises_pass: dict[str, float]) -> list[str]:
    cps = [s for s in segments if s["segment_type"] in ("checkpoint", "exit_check") and s["is_required"]]
    labs = [s for s in segments if s["segment_type"] == "exercise" and s["is_required"]]
    out = []
    if cps:
        out.append(f"Answer {len(cps)} knowledge check{'s' if len(cps) != 1 else ''} (including the exit check).")
    for lab in labs:
        mark = exercises_pass.get(lab.get("exercise_id") or "")
        out.append(f"Pass the practical lab{f' with at least {mark:g}%' if mark is not None else ''}.")
    out.append("Completion is confirmed by the server, not by finishing the videos.")
    return out


@router.get("/lectures/{lecture_id}", response_model=LectureManifest)
async def get_lecture(lecture_id: str, user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)):
    lec = await repo.get_published_lecture(_uuid(lecture_id))
    if not lec:
        raise ApiError(404, "NOT_FOUND")
    if user.role == "learner":
        await ensure_enrolled(repo, user.id, lec["course_id"])
        await ensure_available(repo, user.id, lec)
    segments = []
    raw = await repo.list_segments(lec["id"])
    try:
        for seg in raw:
            cp = await repo.get_checkpoint_with_question(seg["checkpoint_id"]) if seg.get("checkpoint_id") else None
            segments.append(build_segment(seg, cp, user.id))
    except ManifestError as e:
        raise ApiError(500, "CONTENT_CONFIGURATION_ERROR", "This lecture is not set up correctly yet.") from e
    passes: dict[str, float] = {}
    for seg in raw:
        if seg.get("exercise_id"):
            ex = await repo.get_published_exercise(seg["exercise_id"])
            if ex:
                passes[ex["id"]] = float(ex["pass_threshold"])
    prereq_ids = lec.get("prerequisites") or []
    titles = (await repo.titles(prereq_ids, [], []))["lectures"] if prereq_ids else {}
    return LectureManifest(
        id=lec["id"], lecture_number=lec["lecture_number"], title=lec["title"], summary=lec["summary"],
        learning_objectives=lec["learning_objectives"], duration_seconds=lec["duration_seconds"],
        content_version=lec["content_version"], segments=segments,
        estimated_minutes=round(lec["duration_seconds"] / 60) if lec.get("duration_seconds") else None,
        prerequisites=[Prereq(id=p, title=titles.get(p, "Earlier lecture")) for p in prereq_ids],
        completion_criteria=_criteria(raw, passes), attempt_policy=ATTEMPT_POLICY,
    )
