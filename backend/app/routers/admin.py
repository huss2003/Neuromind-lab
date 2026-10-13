"""Administrative operations (§3, §13.3): roles, enrolments and teacher assignment. Admin only; every change is audited."""
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.auth import CurrentUser, require_roles
from app.errors import ApiError
from app.repository import Repository, get_repository
from app.routers.deps import path_uuid
from app.services import audit

router = APIRouter(prefix="/api/v1/admin")
guard = require_roles("admin")


class RoleBody(BaseModel):
    role: Literal["learner", "teacher", "admin"]


@router.patch("/users/{user_id}/role")
async def change_role(user_id: str, body: RoleBody, request: Request, admin: CurrentUser = Depends(guard),
                      repo: Repository = Depends(get_repository)):
    user_id = path_uuid(user_id)
    if user_id == admin.id:
        raise ApiError(400, "CANNOT_CHANGE_OWN_ROLE", "Ask another administrator to change your role.")
    previous = await repo.set_role(user_id, body.role)
    if previous is None:
        raise ApiError(404, "NOT_FOUND")
    await audit.record(repo, request, admin.id, "admin.role_changed", "user", user_id,
                       {"previous_role": previous, "new_role": body.role})
    return {"user_id": user_id, "role": body.role, "previous_role": previous}


async def _need(repo: Repository, user_id: str, role: str) -> None:
    prof = await repo.get_profile(user_id)
    if not prof or prof["role"] != role:
        raise ApiError(404, "NOT_FOUND")


@router.put("/courses/{course_id}/enrollments/{learner_id}", status_code=204)
async def enrol(course_id: str, learner_id: str, request: Request, admin: CurrentUser = Depends(guard),
                repo: Repository = Depends(get_repository)):
    course_id, learner_id = path_uuid(course_id), path_uuid(learner_id)
    if not await repo.get_published_course(course_id):
        raise ApiError(404, "NOT_FOUND")
    await _need(repo, learner_id, "learner")
    await repo.upsert_enrollment(learner_id, course_id)
    await audit.record(repo, request, admin.id, "admin.enrolled", "enrollment", learner_id, {"course_id": course_id})


@router.delete("/courses/{course_id}/enrollments/{learner_id}", status_code=204)
async def unenrol(course_id: str, learner_id: str, request: Request, admin: CurrentUser = Depends(guard),
                  repo: Repository = Depends(get_repository)):
    course_id, learner_id = path_uuid(course_id), path_uuid(learner_id)
    await repo.revoke_enrollment(learner_id, course_id)
    await audit.record(repo, request, admin.id, "admin.unenrolled", "enrollment", learner_id, {"course_id": course_id})


@router.put("/courses/{course_id}/teachers/{teacher_id}/learners/{learner_id}", status_code=204)
async def assign(course_id: str, teacher_id: str, learner_id: str, request: Request, admin: CurrentUser = Depends(guard),
                 repo: Repository = Depends(get_repository)):
    course_id, teacher_id, learner_id = path_uuid(course_id), path_uuid(teacher_id), path_uuid(learner_id)
    if not await repo.get_published_course(course_id):
        raise ApiError(404, "NOT_FOUND")
    await _need(repo, learner_id, "learner")
    prof = await repo.get_profile(teacher_id)
    if not prof or prof["role"] not in ("teacher", "admin"):
        raise ApiError(404, "NOT_FOUND")
    await repo.upsert_assignment(teacher_id, learner_id, course_id)
    await audit.record(repo, request, admin.id, "admin.teacher_assigned", "assignment", learner_id,
                       {"course_id": course_id})


@router.delete("/courses/{course_id}/teachers/{teacher_id}/learners/{learner_id}", status_code=204)
async def unassign(course_id: str, teacher_id: str, learner_id: str, request: Request, admin: CurrentUser = Depends(guard),
                   repo: Repository = Depends(get_repository)):
    course_id, teacher_id, learner_id = path_uuid(course_id), path_uuid(teacher_id), path_uuid(learner_id)
    await repo.revoke_assignment(teacher_id, learner_id, course_id)
    await audit.record(repo, request, admin.id, "admin.teacher_unassigned", "assignment", learner_id,
                       {"course_id": course_id})
