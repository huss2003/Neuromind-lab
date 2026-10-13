import re

from app.errors import ApiError

UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def path_uuid(value: str) -> str:
    """Malformed ids are indistinguishable from unknown ones (404)."""
    if not UUID_RE.match(value):
        raise ApiError(404, "NOT_FOUND")
    return value.lower()


def idempotency_key(value: str | None) -> str:
    if not value or not UUID_RE.match(value):
        raise ApiError(422, "VALIDATION_ERROR", details=[{"field": "Idempotency-Key", "issue": "Must be a UUID"}])
    return value.lower()
