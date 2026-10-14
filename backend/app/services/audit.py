"""Security/assessment audit events (§15.3). Best-effort: an audit failure never breaks the request.
Only allow-listed, non-sensitive metadata is stored (never tokens, source code, answers or tests)."""
import logging
from typing import Any

from fastapi import Request

from app.repository import Repository

log = logging.getLogger("neuromind.audit")
ALLOWED_META = {"status", "score", "role", "reason", "count", "lecture_id", "exercise_id", "checkpoint_id",
                "submission_id", "hint_index", "published", "path", "previous_role", "new_role", "course_id",
                "cohort_id", "announcement_id", "issue_id", "category", "serial", "active", "target_id", "limit", "lecture_number", "tables"}


async def record(repo: Repository, request: Request | None, actor_id: str | None, event: str, resource_type: str,
                 resource_id: str | None = None, metadata: dict[str, Any] | None = None) -> None:
    meta = {k: v for k, v in (metadata or {}).items() if k in ALLOWED_META}
    try:
        await repo.insert_audit({
            "actor_id": actor_id, "event_type": event, "resource_type": resource_type, "resource_id": resource_id,
            "request_id": getattr(request.state, "request_id", None) if request else None, "metadata": meta})
    except Exception as exc:  # noqa: BLE001 - must never break the request
        log.warning("audit write failed: %s", type(exc).__name__)
