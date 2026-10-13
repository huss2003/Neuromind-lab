from fastapi import APIRouter, Depends, HTTPException

from app.auth import CurrentUser, current_user
from app.repository import Repository, get_repository
from app.routers.deps import path_uuid as _uuid
from app.services.manifest import LectureManifest, ManifestError, build_segment

router = APIRouter(prefix="/api/v1")


@router.get("/courses")
async def list_courses(_: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)):
    return {"courses": await repo.list_published_courses()}


@router.get("/courses/{course_id}")
async def get_course(course_id: str, _: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)):
    course = await repo.get_published_course(_uuid(course_id))
    if not course:
        raise HTTPException(404)
    lectures = await repo.list_published_lectures(course["id"])
    modules = await repo.list_published_modules(course["id"])
    grouped = [{**m, "lectures": [x for x in lectures if x.get("module_id") == m["id"]]} for m in modules]
    return {**course, "lectures": lectures, "modules": grouped}


@router.get("/lectures/{lecture_id}", response_model=LectureManifest)
async def get_lecture(lecture_id: str, _: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)):
    lec = await repo.get_published_lecture(_uuid(lecture_id))
    if not lec:
        raise HTTPException(404)
    segments = []
    try:
        for seg in await repo.list_segments(lec["id"]):
            cp = await repo.get_checkpoint_with_question(seg["checkpoint_id"]) if seg.get("checkpoint_id") else None
            segments.append(build_segment(seg, cp))
    except ManifestError as e:
        raise HTTPException(500, detail="content configuration error") from e
    return LectureManifest(
        id=lec["id"], lecture_number=lec["lecture_number"], title=lec["title"], summary=lec["summary"],
        learning_objectives=lec["learning_objectives"], duration_seconds=lec["duration_seconds"],
        content_version=lec["content_version"], segments=segments,
    )
