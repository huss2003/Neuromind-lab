"""Learner-facing extras: certificates (issued by the server), portfolio evidence, announcements, issue reports."""
import re
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.auth import CurrentUser, current_user
from app.errors import ApiError
from app.repository import Repository, get_repository
from app.routers.deps import path_uuid
from app.services import audit

router = APIRouter(prefix="/api/v1")
SERIAL_RE = re.compile(r"^NM-\d{4}-[0-9A-F]{8}$")
ISSUES_PER_HOUR = 5


def _masked_name(name: str) -> str:
    parts = name.split()
    return " ".join([parts[0], parts[-1][0] + "."]) if len(parts) > 1 else (parts[0] if parts else "Learner")


@router.get("/me/certificates")
async def my_certificates(user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)):
    rows, _ = await repo.tbl_select("certificates", [("learner_id", "eq", user.id), ("revoked_at", "is_null", True)], order="issued_at.desc")
    out = []
    for c in rows:
        course = await repo.get_published_course(c["course_id"])
        out.append({"id": c["id"], "serial": c["serial"], "course": course["title"] if course else "Course",
                    "issued_at": c["issued_at"], "completed_lectures": c["completed_lectures"], "holder": user.display_name or user.email})
    return {"certificates": out}


@router.get("/certificates/verify/{serial}")
async def verify_certificate(serial: str, repo: Repository = Depends(get_repository)):
    """Public check that a serial is genuine. Reveals only the course, the issue date and a masked holder name."""
    serial = serial.upper()
    if not SERIAL_RE.match(serial):
        return {"valid": False}
    rows, _ = await repo.tbl_select("certificates", [("serial", "eq", serial), ("revoked_at", "is_null", True)], limit=1)
    if not rows:
        return {"valid": False}
    c = rows[0]
    course = await repo.get_published_course(c["course_id"])
    profile = await repo.get_profile(c["learner_id"])
    return {"valid": True, "serial": serial, "course": course["title"] if course else "Course", "issued_at": c["issued_at"],
            "holder": _masked_name((profile or {}).get("display_name", ""))}


class PortfolioBody(BaseModel):
    submission_id: str
    title: str = Field(min_length=1, max_length=120)
    note: str = Field(default="", max_length=1000)


@router.get("/me/portfolio")
async def my_portfolio(user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)):
    items, _ = await repo.tbl_select("portfolio_items", [("learner_id", "eq", user.id)], order="created_at.desc")
    out = []
    for it in items:
        sub = await repo.get_submission(it["submission_id"])
        if not sub or sub["learner_id"] != user.id:
            continue
        titles = await repo.titles([], [], [it["exercise_id"]])
        out.append({"id": it["id"], "title": it["title"], "note": it["note"], "created_at": it["created_at"],
                    "exercise": titles["exercises"].get(it["exercise_id"]), "score": float(sub["score"]) if sub.get("score") is not None else None,
                    "submission_id": sub["id"], "source_code": sub["source_code"]})
    return {"items": out}


@router.post("/me/portfolio", status_code=201)
async def add_portfolio(body: PortfolioBody, request: Request, user: CurrentUser = Depends(current_user),
                        repo: Repository = Depends(get_repository)):
    """Only the learner's own PASSED official submissions can be added; the same submission is never added twice."""
    sub = await repo.get_submission(path_uuid(body.submission_id))
    if not sub or sub["learner_id"] != user.id:
        raise ApiError(404, "NOT_FOUND")
    if sub["status"] != "passed":
        raise ApiError(422, "VALIDATION_ERROR", details=[{"field": "submission_id", "issue": "Only passed submissions can be added"}])
    row = await repo.tbl_insert("portfolio_items", {"learner_id": user.id, "submission_id": sub["id"], "exercise_id": sub["exercise_id"],
                                                    "title": body.title.strip(), "note": body.note.strip()}, ignore_duplicates=True)
    if row is None:
        existing, _ = await repo.tbl_select("portfolio_items", [("submission_id", "eq", sub["id"])], limit=1)
        return {"id": existing[0]["id"], "already_added": True}
    await audit.record(repo, request, user.id, "portfolio.added", "portfolio", row["id"], {"submission_id": sub["id"]})
    return {"id": row["id"], "already_added": False}


@router.delete("/me/portfolio/{item_id}", status_code=204)
async def remove_portfolio(item_id: str, request: Request, user: CurrentUser = Depends(current_user),
                           repo: Repository = Depends(get_repository)):
    removed = await repo.tbl_delete("portfolio_items", [("id", "eq", path_uuid(item_id)), ("learner_id", "eq", user.id)])
    if not removed:
        raise ApiError(404, "NOT_FOUND")
    await audit.record(repo, request, user.id, "portfolio.removed", "portfolio", item_id)


@router.get("/me/announcements")
async def my_announcements(user: CurrentUser = Depends(current_user), repo: Repository = Depends(get_repository)):
    """Course-wide announcements from administrators, and announcements from the learner's own (currently assigned) teachers."""
    courses = await repo.list_enrolled_course_ids(user.id)
    if not courses:
        return {"announcements": []}
    teachers = set(await repo.list_teacher_ids_for_learner(user.id))
    rows, _ = await repo.tbl_select("announcements", [("course_id", "in", courses), ("archived_at", "is_null", True)],
                                    order="created_at.desc", limit=50)
    visible = [a for a in rows if a["scope"] == "course" or a["author_id"] in teachers]
    names = {}
    for aid in {a["author_id"] for a in visible}:
        p = await repo.get_profile(aid)
        names[aid] = (p or {}).get("display_name") or "Your teacher"
    return {"announcements": [{"id": a["id"], "title": a["title"], "body": a["body"], "created_at": a["created_at"],
                               "from": names[a["author_id"]]} for a in visible[:20]]}


class IssueBody(BaseModel):
    category: Literal["content", "grading", "account", "accessibility", "other"]
    message: str = Field(min_length=5, max_length=2000)
    page: str | None = Field(default=None, max_length=300)


@router.post("/me/issues", status_code=201)
async def report_issue(body: IssueBody, request: Request, user: CurrentUser = Depends(current_user),
                       repo: Repository = Depends(get_repository)):
    """Anyone signed in can report a problem. Rate limited per person; never include secrets (the page says so)."""
    since = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    _, recent = await repo.tbl_select("issue_reports", [("reporter_id", "eq", user.id), ("created_at", "gte", since)], limit=1)
    if recent >= ISSUES_PER_HOUR:
        raise ApiError(429, "RATE_LIMITED", "You have sent several reports in the last hour. Please wait before sending another.")
    row = await repo.tbl_insert("issue_reports", {"reporter_id": user.id, "category": body.category, "message": body.message.strip(),
                                                  "page": (body.page or None), "status": "open",
                                                  "correlation_id": getattr(request.state, "request_id", None)})
    await audit.record(repo, request, user.id, "issue.reported", "issue", row["id"], {"issue_id": row["id"], "category": body.category})
    return {"id": row["id"], "reference": row["id"][:8].upper()}
