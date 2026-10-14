"""Teacher tools: announcements to assigned learners, cohort overview, progress report export (JSON or CSV)."""
import csv
import io
from typing import Any, Literal

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.auth import CurrentUser, require_roles
from app.errors import ApiError
from app.repository import Repository, get_repository
from app.routers.deps import path_uuid
from app.routers.teacher import _scope, _summary
from app.services import audit
from app.services.grading import best_valid_score

router = APIRouter(prefix="/api/v1/teacher")
guard = require_roles("teacher", "admin")


class AnnouncementBody(BaseModel):
    course_id: str
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=2000)
    scope: Literal["assigned", "course"] = "assigned"


@router.post("/announcements", status_code=201)
async def create_announcement(body: AnnouncementBody, request: Request, user: CurrentUser = Depends(guard),
                              repo: Repository = Depends(get_repository)):
    """Teachers write to their own assigned learners; only administrators may address a whole course."""
    course_id = path_uuid(body.course_id)
    if not await repo.get_published_course(course_id):
        raise ApiError(404, "NOT_FOUND")
    if body.scope == "course" and user.role != "admin":
        raise ApiError(403, "FORBIDDEN", "Only administrators can announce to a whole course")
    row = await repo.tbl_insert("announcements", {"author_id": user.id, "course_id": course_id, "scope": body.scope,
                                                  "title": body.title.strip(), "body": body.body.strip()})
    await audit.record(repo, request, user.id, "announcement.created", "announcement", row["id"],
                       {"announcement_id": row["id"], "course_id": course_id})
    return {"id": row["id"]}


@router.get("/announcements")
async def my_announcements(user: CurrentUser = Depends(guard), repo: Repository = Depends(get_repository)):
    filters: list[Any] = [("archived_at", "is_null", True)]
    if user.role != "admin":
        filters.append(("author_id", "eq", user.id))
    rows, _t = await repo.tbl_select("announcements", filters, order="created_at.desc", limit=50)
    return {"announcements": [{"id": a["id"], "title": a["title"], "body": a["body"], "scope": a["scope"], "course_id": a["course_id"],
                               "created_at": a["created_at"]} for a in rows]}


@router.delete("/announcements/{announcement_id}", status_code=204)
async def archive_announcement(announcement_id: str, request: Request, user: CurrentUser = Depends(guard),
                               repo: Repository = Depends(get_repository)):
    aid = path_uuid(announcement_id)
    filters: list[Any] = [("id", "eq", aid), ("archived_at", "is_null", True)]
    if user.role != "admin":
        filters.append(("author_id", "eq", user.id))
    rows = await repo.tbl_update("announcements", filters, {"archived_at": datetime.now(UTC).isoformat()})
    if not rows:
        raise ApiError(404, "NOT_FOUND")
    await audit.record(repo, request, user.id, "announcement.archived", "announcement", aid, {"announcement_id": aid})


async def _cohorts_for(user: CurrentUser, repo: Repository) -> list[dict[str, Any]]:
    cohorts, _t = await repo.tbl_select("cohorts", [("archived_at", "is_null", True)], order="created_at.asc")
    if user.role == "admin":
        return cohorts
    mine, _m = await repo.tbl_select("cohort_teachers", [("teacher_id", "eq", user.id)], columns="cohort_id")
    ids = {m["cohort_id"] for m in mine}
    return [c for c in cohorts if c["id"] in ids]


@router.get("/cohorts")
async def cohorts(user: CurrentUser = Depends(guard), repo: Repository = Depends(get_repository)):
    out = []
    for c in await _cohorts_for(user, repo):
        members, _m = await repo.tbl_select("cohort_members", [("cohort_id", "eq", c["id"])], columns="learner_id")
        sums = [await _summary(repo, m["learner_id"]) for m in members[:100]]
        out.append({"id": c["id"], "name": c["name"], "course_id": c["course_id"], "learners": len(members),
                    "lectures_completed": sum(s["lectures_completed"] for s in sums),
                    "in_progress": sum(s["lectures_in_progress"] > 0 for s in sums), "needs_support": sum(s["needs_support"] for s in sums)})
    return {"cohorts": out}


def _safe_cell(value: Any) -> str:
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text  # blocks spreadsheet formula injection


@router.get("/reports/progress")
async def progress_report(request: Request, format: Literal["json", "csv"] = "json", cohort_id: str | None = None,
                          user: CurrentUser = Depends(guard), repo: Repository = Depends(get_repository)):
    """Progress per learner within the teacher's own scope (an administrator sees everyone, or one cohort)."""
    scope = await _scope(user, repo)
    if cohort_id:
        cid = path_uuid(cohort_id)
        allowed = {c["id"] for c in await _cohorts_for(user, repo)}
        if cid not in allowed:
            raise ApiError(404, "NOT_FOUND")
        members, _m = await repo.tbl_select("cohort_members", [("cohort_id", "eq", cid)], columns="learner_id")
        ids = [m["learner_id"] for m in members]
        scope = ids if scope is None else [i for i in ids if i in scope]
    learners, _t = await repo.list_learners_page(scope, None, 100, 0)
    rows = []
    for lr in learners:
        s = await _summary(repo, lr["id"])
        subs = await repo.list_learner_submissions(lr["id"])
        by_ex: dict[str, list] = {}
        for x in subs:
            by_ex.setdefault(x["exercise_id"], []).append(x)
        bests = [b for b in (best_valid_score(v) for v in by_ex.values()) if b is not None]
        rows.append({"learner": lr["display_name"], "lectures_completed": s["lectures_completed"], "lectures_in_progress": s["lectures_in_progress"],
                     "exercises_passed": sum(any(x["status"] == "passed" for x in v) for v in by_ex.values()), "attempts": len(subs),
                     "average_best_score": round(sum(bests) / len(bests), 1) if bests else None, "needs_support": s["needs_support"],
                     "last_active": s["last_active"]})
    await audit.record(repo, request, user.id, "teacher.report_exported", "report", None, {"count": len(rows)})
    if format == "json":
        return {"rows": rows}
    buf = io.StringIO()
    w = csv.writer(buf)
    cols = list(rows[0].keys()) if rows else ["learner", "lectures_completed", "lectures_in_progress", "exercises_passed", "attempts",
                                               "average_best_score", "needs_support", "last_active"]
    w.writerow(cols)
    for r in rows:
        w.writerow([_safe_cell(r[c]) for c in cols])
    return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="progress-report.csv"'})
