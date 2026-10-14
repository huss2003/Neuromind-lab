"""Administrator workspace API: users, overview, grading queue, audit log, content status, cohorts, issue queue, settings.
Administrators only. Every change is audited. There is deliberately no endpoint that edits an official score."""
import os
import re
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from app.auth import CurrentUser, require_roles
from app.auth_admin import AuthAdmin, get_auth_admin
from app.errors import ApiError
from app.repository import Repository, get_repository
from app.routers.deps import path_uuid
from app.services import audit, metrics

router = APIRouter(prefix="/api/v1/admin")
guard = require_roles("admin")
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s]{2,}$")
DEAD_LETTER_CLAIMS = 3  # keep in step with routers/worker.py MAX_CLAIMS


def _now() -> str:
    return datetime.now(UTC).isoformat()


# ---------- users ----------
@router.get("/users")
async def list_users(q: str | None = Query(default=None, max_length=60), role: Literal["any", "learner", "teacher", "admin"] = "any",
                     status: Literal["any", "active", "deactivated"] = "any", limit: int = Query(default=25, ge=1, le=100),
                     offset: int = Query(default=0, ge=0), _: CurrentUser = Depends(guard),
                     repo: Repository = Depends(get_repository), auth_admin: AuthAdmin = Depends(get_auth_admin)):
    profiles, _total = await repo.tbl_select("profiles", columns="id,display_name,role,deactivated_at,created_at", limit=1000)
    by_id = {p["id"]: p for p in profiles}
    rows = []
    for u in await auth_admin.list_users():
        p = by_id.get(u["id"])
        if not p:
            continue
        rows.append({"id": u["id"], "email": u["email"], "display_name": p["display_name"], "role": p["role"],
                     "deactivated": bool(p.get("deactivated_at")), "last_sign_in_at": u.get("last_sign_in_at"),
                     "created_at": p["created_at"], "email_confirmed": u.get("email_confirmed", True)})
    if q:
        needle = q.lower()
        rows = [r for r in rows if needle in r["email"].lower() or needle in (r["display_name"] or "").lower()]
    if role != "any":
        rows = [r for r in rows if r["role"] == role]
    if status != "any":
        rows = [r for r in rows if r["deactivated"] == (status == "deactivated")]
    rows.sort(key=lambda r: ((r["display_name"] or r["email"]).lower()))
    return {"users": rows[offset:offset + limit], "total": len(rows), "limit": limit, "offset": offset}


class NewUser(BaseModel):
    email: str = Field(max_length=320)
    display_name: str = Field(min_length=1, max_length=80)
    role: Literal["learner", "teacher", "admin"] = "learner"
    password: str = Field(min_length=12, max_length=128)
    course_id: str | None = None


@router.post("/users", status_code=201)
async def create_user(body: NewUser, request: Request, admin: CurrentUser = Depends(guard), repo: Repository = Depends(get_repository),
                      auth_admin: AuthAdmin = Depends(get_auth_admin)):
    email = body.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise ApiError(422, "VALIDATION_ERROR", details=[{"field": "email", "issue": "Not a valid email address"}])
    if body.password.lower() == email:
        raise ApiError(422, "VALIDATION_ERROR", details=[{"field": "password", "issue": "Choose a different password"}])
    course_id = path_uuid(body.course_id) if body.course_id else None
    if course_id and not await repo.get_published_course(course_id):
        raise ApiError(404, "NOT_FOUND")
    created = await auth_admin.create_user(email, body.password, body.display_name.strip())
    if not created:  # same message whether the address exists or the password was refused
        raise ApiError(409, "USER_NOT_CREATED", "The account could not be created. The address may already be registered, or the password was refused.")
    await repo.tbl_update("profiles", [("id", "eq", created["id"])], {"role": body.role, "display_name": body.display_name.strip()})
    if course_id and body.role == "learner":
        await repo.upsert_enrollment(created["id"], course_id)
    await audit.record(repo, request, admin.id, "admin.user_created", "user", created["id"], {"target_id": created["id"], "new_role": body.role})
    return {"id": created["id"], "email": email, "role": body.role}


async def _set_active(user_id: str, active: bool, request: Request, admin: CurrentUser, repo: Repository, auth_admin: AuthAdmin):
    user_id = path_uuid(user_id)
    if user_id == admin.id:
        raise ApiError(400, "CANNOT_CHANGE_OWN_ACCOUNT", "Ask another administrator to change your account.")
    if not await repo.get_profile(user_id):
        raise ApiError(404, "NOT_FOUND")
    await repo.tbl_update("profiles", [("id", "eq", user_id)], {"deactivated_at": None if active else _now()})
    banned_ok = await auth_admin.set_banned(user_id, not active)
    await audit.record(repo, request, admin.id, "admin.user_reactivated" if active else "admin.user_deactivated", "user", user_id,
                       {"target_id": user_id, "active": active})
    return {"user_id": user_id, "active": active, "sign_in_blocked": banned_ok}


@router.post("/users/{user_id}/deactivate")
async def deactivate(user_id: str, request: Request, admin: CurrentUser = Depends(guard), repo: Repository = Depends(get_repository),
                     auth_admin: AuthAdmin = Depends(get_auth_admin)):
    return await _set_active(user_id, False, request, admin, repo, auth_admin)


@router.post("/users/{user_id}/reactivate")
async def reactivate(user_id: str, request: Request, admin: CurrentUser = Depends(guard), repo: Repository = Depends(get_repository),
                     auth_admin: AuthAdmin = Depends(get_auth_admin)):
    return await _set_active(user_id, True, request, admin, repo, auth_admin)


# ---------- overview, queue ----------
@router.get("/overview")
async def overview(_: CurrentUser = Depends(guard), repo: Repository = Depends(get_repository)):
    profiles, _t = await repo.tbl_select("profiles", columns="role,deactivated_at", limit=1000)
    since = (datetime.now(UTC) - timedelta(hours=24)).isoformat()
    _, open_issues = await repo.tbl_select("issue_reports", [("status", "eq", "open")], limit=1)
    _, dead = await repo.tbl_select("lab_submissions", [("status", "eq", "error"), ("claim_count", "gte", DEAD_LETTER_CLAIMS)], limit=1)
    courses, _c = await repo.tbl_select("courses", columns="id,status")
    lectures, _l = await repo.tbl_select("lectures", columns="id,status")
    return {
        "users": {"learners": sum(p["role"] == "learner" for p in profiles), "teachers": sum(p["role"] == "teacher" for p in profiles),
                  "admins": sum(p["role"] == "admin" for p in profiles), "deactivated": sum(bool(p.get("deactivated_at")) for p in profiles)},
        "content": {"courses_published": sum(c["status"] == "published" for c in courses),
                    "lectures_published": sum(x["status"] == "published" for x in lectures), "lectures_total": len(lectures)},
        "queue": await repo.queue_stats(), "grading_24h": metrics.summarise(await repo.queue_metrics(since)),
        "dead_letters": dead, "open_issues": open_issues,
        "health": {"api": True, "database": await repo.ping(), "checked_at": _now()},
    }


@router.get("/queue")
async def queue(_: CurrentUser = Depends(guard), repo: Repository = Depends(get_repository)):
    since = (datetime.now(UTC) - timedelta(hours=24)).isoformat()
    dead, _t = await repo.tbl_select("lab_submissions", [("status", "eq", "error"), ("claim_count", "gte", DEAD_LETTER_CLAIMS)],
                                     columns="id,learner_id,exercise_id,created_at,finished_at,claim_count", order="created_at.desc", limit=50)
    return {"queue": await repo.queue_stats(), "grading_24h": metrics.summarise(await repo.queue_metrics(since)),
            "dead_letters": [{"submission_id": d["id"], "exercise_id": d["exercise_id"], "created_at": d["created_at"],
                              "claim_count": d.get("claim_count")} for d in dead],
            "procedure": "Open the failure reason in the runbook (docs/06-operations/DEAD_LETTER_RUNBOOK.md), confirm the worker is healthy, then requeue."}


@router.post("/submissions/{submission_id}/requeue")
async def requeue(submission_id: str, request: Request, admin: CurrentUser = Depends(guard), repo: Repository = Depends(get_repository)):
    """Give a dead-lettered attempt another full set of claims. Only system-error attempts qualify; a learner's own failure never does."""
    sid = path_uuid(submission_id)
    rows = await repo.tbl_update("lab_submissions", [("id", "eq", sid), ("status", "eq", "error"), ("claim_count", "gte", DEAD_LETTER_CLAIMS)], {
        "status": "queued", "claim_count": 0, "claimed_by": None, "lease_expires_at": None, "finished_at": None, "safe_feedback": []})
    if not rows:
        raise ApiError(404, "NOT_FOUND", "No dead-lettered attempt with that id")
    await audit.record(repo, request, admin.id, "admin.submission_requeued", "submission", sid, {"submission_id": sid})
    return {"submission_id": sid, "status": "queued"}


# ---------- audit log ----------
@router.get("/audit")
async def audit_log(event_type: str | None = Query(default=None, max_length=60), actor_id: str | None = None,
                    limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0),
                    _: CurrentUser = Depends(guard), repo: Repository = Depends(get_repository)):
    filters: list[Any] = []
    if event_type:
        filters.append(("event_type", "eq", event_type))
    if actor_id:
        filters.append(("actor_id", "eq", path_uuid(actor_id)))
    rows, total = await repo.tbl_select("audit_logs", filters, columns="id,actor_id,event_type,resource_type,resource_id,request_id,metadata,created_at",
                                        order="created_at.desc", limit=limit, offset=offset)
    return {"events": rows, "total": total, "limit": limit, "offset": offset}


# ---------- content ----------
@router.get("/courses")
async def courses_overview(_: CurrentUser = Depends(guard), repo: Repository = Depends(get_repository)):
    courses, _c = await repo.tbl_select("courses", columns="id,title,status", order="created_at.asc")
    lectures, _l = await repo.tbl_select("lectures", columns="id,course_id,lecture_number,title,status,content_version,published_at", order="lecture_number.asc")
    exercises, _e = await repo.tbl_select("lecture_exercises", columns="id,lecture_id,title,status,test_suite_version,pass_threshold,max_attempts")
    enrolled, _n = await repo.tbl_select("enrollments", [("revoked_at", "is_null", True)], columns="course_id,learner_id")
    out = []
    for c in courses:
        lecs = [x for x in lectures if x["course_id"] == c["id"]]
        out.append({**c, "learners_enrolled": sum(e["course_id"] == c["id"] for e in enrolled),
                    "lectures": [{**x, "exercises": [{k: v for k, v in e.items() if k != "lecture_id"} for e in exercises if e["lecture_id"] == x["id"]]} for x in lecs]})
    return {"courses": out, "note": "Published content is cached for up to 15 seconds, so a status change can take that long to appear for learners."}


class LectureStatus(BaseModel):
    status: Literal["draft", "published", "archived"]


@router.patch("/lectures/{lecture_id}/status")
async def set_lecture_status(lecture_id: str, body: LectureStatus, request: Request, admin: CurrentUser = Depends(guard),
                             repo: Repository = Depends(get_repository)):
    lid = path_uuid(lecture_id)
    rows, _t = await repo.tbl_select("lectures", [("id", "eq", lid)], columns="id,status", limit=1)
    if not rows:
        raise ApiError(404, "NOT_FOUND")
    if body.status == "published" and not await repo.list_segments(lid):
        raise ApiError(422, "VALIDATION_ERROR", "A lecture with no sections cannot be published",
                       [{"field": "status", "issue": "The lecture has no sections"}])
    fields: dict[str, Any] = {"status": body.status}
    if body.status == "published":
        fields["published_at"] = _now()
    await repo.tbl_update("lectures", [("id", "eq", lid)], fields)
    await audit.record(repo, request, admin.id, "admin.lecture_status_changed", "lecture", lid, {"lecture_id": lid, "status": body.status})
    return {"lecture_id": lid, "status": body.status, "previous_status": rows[0]["status"]}


# ---------- cohorts ----------
class CohortBody(BaseModel):
    course_id: str
    name: str = Field(min_length=1, max_length=80)


async def _cohort(repo: Repository, cohort_id: str) -> dict[str, Any]:
    rows, _t = await repo.tbl_select("cohorts", [("id", "eq", path_uuid(cohort_id)), ("archived_at", "is_null", True)], limit=1)
    if not rows:
        raise ApiError(404, "NOT_FOUND")
    return rows[0]


@router.get("/cohorts")
async def list_cohorts(_: CurrentUser = Depends(guard), repo: Repository = Depends(get_repository)):
    cohorts, _t = await repo.tbl_select("cohorts", [("archived_at", "is_null", True)], order="created_at.asc")
    out = []
    for c in cohorts:
        members, _m = await repo.tbl_select("cohort_members", [("cohort_id", "eq", c["id"])], columns="learner_id")
        teachers, _x = await repo.tbl_select("cohort_teachers", [("cohort_id", "eq", c["id"])], columns="teacher_id")
        names = {}
        for pid in [m["learner_id"] for m in members] + [t["teacher_id"] for t in teachers]:
            names[pid] = ((await repo.get_profile(pid)) or {}).get("display_name") or "Unknown"
        out.append({"id": c["id"], "course_id": c["course_id"], "name": c["name"], "created_at": c["created_at"],
                    "learners": [{"id": m["learner_id"], "display_name": names[m["learner_id"]]} for m in members],
                    "teachers": [{"id": t["teacher_id"], "display_name": names[t["teacher_id"]]} for t in teachers]})
    return {"cohorts": out}


@router.post("/cohorts", status_code=201)
async def create_cohort(body: CohortBody, request: Request, admin: CurrentUser = Depends(guard), repo: Repository = Depends(get_repository)):
    course_id = path_uuid(body.course_id)
    if not await repo.get_published_course(course_id):
        raise ApiError(404, "NOT_FOUND")
    try:
        row = await repo.tbl_insert("cohorts", {"course_id": course_id, "name": body.name.strip(), "created_by": admin.id})
    except Exception:  # noqa: BLE001 - unique (course, name)
        raise ApiError(409, "COHORT_EXISTS", "A cohort with that name already exists for this course") from None
    await audit.record(repo, request, admin.id, "admin.cohort_created", "cohort", row["id"], {"cohort_id": row["id"], "course_id": course_id})
    return {"id": row["id"], "name": row["name"]}


@router.delete("/cohorts/{cohort_id}", status_code=204)
async def archive_cohort(cohort_id: str, request: Request, admin: CurrentUser = Depends(guard), repo: Repository = Depends(get_repository)):
    c = await _cohort(repo, cohort_id)
    await repo.tbl_update("cohorts", [("id", "eq", c["id"])], {"archived_at": _now()})
    await audit.record(repo, request, admin.id, "admin.cohort_archived", "cohort", c["id"], {"cohort_id": c["id"]})


async def _shared_elsewhere(repo: Repository, teacher_id: str, learner_id: str, exclude: str) -> bool:
    mine, _t = await repo.tbl_select("cohort_teachers", [("teacher_id", "eq", teacher_id), ("cohort_id", "neq", exclude)], columns="cohort_id")
    for m in mine:
        cohort, _c = await repo.tbl_select("cohorts", [("id", "eq", m["cohort_id"]), ("archived_at", "is_null", True)], limit=1)
        member, _m = await repo.tbl_select("cohort_members", [("cohort_id", "eq", m["cohort_id"]), ("learner_id", "eq", learner_id)], limit=1)
        if cohort and member:
            return True
    return False


@router.put("/cohorts/{cohort_id}/members/{learner_id}", status_code=204)
async def add_member(cohort_id: str, learner_id: str, request: Request, admin: CurrentUser = Depends(guard), repo: Repository = Depends(get_repository)):
    c = await _cohort(repo, cohort_id)
    learner_id = path_uuid(learner_id)
    prof = await repo.get_profile(learner_id)
    if not prof or prof["role"] != "learner":
        raise ApiError(404, "NOT_FOUND")
    await repo.tbl_insert("cohort_members", {"cohort_id": c["id"], "learner_id": learner_id}, ignore_duplicates=True)
    await repo.upsert_enrollment(learner_id, c["course_id"])
    teachers, _t = await repo.tbl_select("cohort_teachers", [("cohort_id", "eq", c["id"])], columns="teacher_id")
    for t in teachers:
        await repo.upsert_assignment(t["teacher_id"], learner_id, c["course_id"])
    await audit.record(repo, request, admin.id, "admin.cohort_member_added", "cohort", c["id"], {"cohort_id": c["id"], "target_id": learner_id})


@router.delete("/cohorts/{cohort_id}/members/{learner_id}", status_code=204)
async def remove_member(cohort_id: str, learner_id: str, request: Request, admin: CurrentUser = Depends(guard), repo: Repository = Depends(get_repository)):
    c = await _cohort(repo, cohort_id)
    learner_id = path_uuid(learner_id)
    await repo.tbl_delete("cohort_members", [("cohort_id", "eq", c["id"]), ("learner_id", "eq", learner_id)])
    teachers, _t = await repo.tbl_select("cohort_teachers", [("cohort_id", "eq", c["id"])], columns="teacher_id")
    for t in teachers:
        if not await _shared_elsewhere(repo, t["teacher_id"], learner_id, c["id"]):
            await repo.revoke_assignment(t["teacher_id"], learner_id, c["course_id"])
    await audit.record(repo, request, admin.id, "admin.cohort_member_removed", "cohort", c["id"], {"cohort_id": c["id"], "target_id": learner_id})


@router.put("/cohorts/{cohort_id}/teachers/{teacher_id}", status_code=204)
async def add_teacher(cohort_id: str, teacher_id: str, request: Request, admin: CurrentUser = Depends(guard), repo: Repository = Depends(get_repository)):
    c = await _cohort(repo, cohort_id)
    teacher_id = path_uuid(teacher_id)
    prof = await repo.get_profile(teacher_id)
    if not prof or prof["role"] not in ("teacher", "admin"):
        raise ApiError(404, "NOT_FOUND")
    await repo.tbl_insert("cohort_teachers", {"cohort_id": c["id"], "teacher_id": teacher_id}, ignore_duplicates=True)
    members, _m = await repo.tbl_select("cohort_members", [("cohort_id", "eq", c["id"])], columns="learner_id")
    for m in members:
        await repo.upsert_assignment(teacher_id, m["learner_id"], c["course_id"])
    await audit.record(repo, request, admin.id, "admin.cohort_teacher_added", "cohort", c["id"], {"cohort_id": c["id"], "target_id": teacher_id})


@router.delete("/cohorts/{cohort_id}/teachers/{teacher_id}", status_code=204)
async def remove_teacher(cohort_id: str, teacher_id: str, request: Request, admin: CurrentUser = Depends(guard), repo: Repository = Depends(get_repository)):
    c = await _cohort(repo, cohort_id)
    teacher_id = path_uuid(teacher_id)
    await repo.tbl_delete("cohort_teachers", [("cohort_id", "eq", c["id"]), ("teacher_id", "eq", teacher_id)])
    members, _m = await repo.tbl_select("cohort_members", [("cohort_id", "eq", c["id"])], columns="learner_id")
    for m in members:
        if not await _shared_elsewhere(repo, teacher_id, m["learner_id"], c["id"]):
            await repo.revoke_assignment(teacher_id, m["learner_id"], c["course_id"])
    await audit.record(repo, request, admin.id, "admin.cohort_teacher_removed", "cohort", c["id"], {"cohort_id": c["id"], "target_id": teacher_id})


# ---------- issue reports ----------
@router.get("/issues")
async def list_issues(status: Literal["any", "open", "triaged", "resolved", "dismissed"] = "open", limit: int = Query(default=25, ge=1, le=100),
                      offset: int = Query(default=0, ge=0), _: CurrentUser = Depends(guard), repo: Repository = Depends(get_repository)):
    filters = [] if status == "any" else [("status", "eq", status)]
    rows, total = await repo.tbl_select("issue_reports", filters, order="created_at.desc", limit=limit, offset=offset)
    out = []
    for r in rows:
        p = await repo.get_profile(r["reporter_id"])
        out.append({"id": r["id"], "reference": r["id"][:8].upper(), "category": r["category"], "message": r["message"], "page": r.get("page"),
                    "status": r["status"], "admin_note": r.get("admin_note"), "created_at": r["created_at"],
                    "reporter": (p or {}).get("display_name") or "Unknown", "correlation_id": r.get("correlation_id")})
    return {"issues": out, "total": total, "limit": limit, "offset": offset}


class IssuePatch(BaseModel):
    status: Literal["open", "triaged", "resolved", "dismissed"]
    admin_note: str | None = Field(default=None, max_length=1000)


@router.patch("/issues/{issue_id}")
async def update_issue(issue_id: str, body: IssuePatch, request: Request, admin: CurrentUser = Depends(guard), repo: Repository = Depends(get_repository)):
    iid = path_uuid(issue_id)
    fields: dict[str, Any] = {"status": body.status, "resolved_by": admin.id if body.status in ("resolved", "dismissed") else None}
    if body.admin_note is not None:
        fields["admin_note"] = body.admin_note.strip() or None
    rows = await repo.tbl_update("issue_reports", [("id", "eq", iid)], fields)
    if not rows:
        raise ApiError(404, "NOT_FOUND")
    await audit.record(repo, request, admin.id, "admin.issue_updated", "issue", iid, {"issue_id": iid, "status": body.status})
    return {"id": iid, "status": body.status}


# ---------- settings (read only) ----------
@router.get("/settings")
async def settings(_: CurrentUser = Depends(guard)):
    """Platform limits as currently configured. Read only: changing them is a deployment (environment variable) change."""
    from app.routers import exercises, worker  # local import: avoids a router import cycle at start-up
    items = [
        ("Grading mode", os.getenv("GRADER_MODE", "inline"), "queue = a private worker grades; inline is for development only"),
        ("Submissions per learner per minute", exercises.MAX_SUBMISSIONS_PER_MINUTE, "Rate limit"),
        ("Submissions in flight per learner", exercises.MAX_IN_FLIGHT, "Concurrency limit"),
        ("Maximum code size (bytes)", os.getenv("MAX_SOURCE_CODE_BYTES", "50000"), "Rejected above this"),
        ("Worker lease (seconds)", worker.LEASE_SECONDS, "A dead worker's job is reclaimed after this"),
        ("Maximum claims before dead-letter", worker.MAX_CLAIMS, "Then the attempt becomes a system error"),
        ("Stale attempt expiry (seconds)", os.getenv("QUEUE_STALE_SECONDS", "900"), "Queued/running longer than this is marked expired"),
        ("Published content cache (seconds)", os.getenv("CONTENT_CACHE_SECONDS", "15"), "Delay before a content status change reaches learners"),
        ("Token check cache (seconds)", os.getenv("AUTH_CACHE_SECONDS", "30"), "Delay before a deactivation reaches an active session"),
        ("Allowed web origins", os.getenv("CORS_ALLOWED_ORIGINS", ""), "Browser origins permitted to call the API"),
    ]
    return {"settings": [{"label": a, "value": str(b), "note": c} for a, b, c in items], "read_only": True}
