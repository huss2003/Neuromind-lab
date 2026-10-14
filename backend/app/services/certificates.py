"""Certificates are issued by the server only, when every published lecture of a course is completed by the learner."""
import secrets
from datetime import UTC, datetime
from typing import Any

from app.repository import Repository

Row = dict[str, Any]


def new_serial() -> str:
    return f"NM-{datetime.now(UTC).year}-{secrets.token_hex(4).upper()}"


async def issue_if_eligible(repo: Repository, learner_id: str, course_id: str) -> tuple[Row | None, bool]:
    """Idempotent. Returns (certificate, newly_issued): the existing one, a new one when the course is fully completed, or (None, False)."""
    existing, _ = await repo.tbl_select("certificates", [("learner_id", "eq", learner_id), ("course_id", "eq", course_id)], limit=1)
    if existing:
        return existing[0], False
    lectures = await repo.list_published_lectures(course_id)
    if not lectures:
        return None, False
    done = {s["lecture_id"] for s in await repo.list_learner_sessions(learner_id) if s["status"] == "completed"}
    if not all(x["id"] in done for x in lectures):
        return None, False
    row = await repo.tbl_insert("certificates", {"learner_id": learner_id, "course_id": course_id, "serial": new_serial(),
                                                 "completed_lectures": len(lectures)}, ignore_duplicates=True)
    if row is None:  # a concurrent request issued it first
        again, _ = await repo.tbl_select("certificates", [("learner_id", "eq", learner_id), ("course_id", "eq", course_id)], limit=1)
        return (again[0] if again else None), False
    return row, True
