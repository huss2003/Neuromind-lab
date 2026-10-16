"""Administrator content import: validate and import lecture packs (see docs/06-operations/CONTENT_PACK_GUIDE.md).
Administrators only. Imports are idempotent upserts and land as drafts unless `publish` is set. Hidden test definitions
travel in the request body, are written only to the server-only exercise_tests table and are never returned or audited."""
import json
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.auth import CurrentUser, require_roles
from app.content_pack import WRITE_ORDER, PackError, build_rows, check_pack
from app.errors import ApiError
from app.repository import Repository, get_repository
from app.services import audit

router = APIRouter(prefix="/api/v1/admin/content")
guard = require_roles("admin")
MAX_BODY_CHARS = 400_000


class PackBody(BaseModel):
    pack: dict[str, Any]
    tests: dict[str, dict[str, Any]] = Field(default_factory=dict)


class ImportBody(PackBody):
    publish: bool = False
    replace_published: bool = False
    course_id: str | None = None


def _check_size(body: PackBody) -> None:
    if len(json.dumps(body.model_dump())) > MAX_BODY_CHARS:
        raise ApiError(413, "PAYLOAD_TOO_LARGE", "The pack is too large (limit about 400 KB)")


def _report(body: PackBody) -> tuple[Any, dict[str, Any]]:
    pack, problems = check_pack(body.pack)
    missing = sorted(t.key for t in pack.lab.tests if t.key not in body.tests) if pack else []
    summary = {"valid": pack is not None and not missing, "problems": problems, "missing_tests": missing}
    if pack:
        summary["summary"] = {"lecture_number": pack.lecture_number, "title": pack.title, "segments": len(pack.segments),
                              "checkpoints": len(pack.checkpoints), "lab_tests": len(pack.lab.tests)}
    return pack, summary


@router.post("/packs/validate")
async def validate_pack(body: PackBody, _: CurrentUser = Depends(guard)):
    _check_size(body)
    return _report(body)[1]


@router.post("/packs/import")
async def import_pack(body: ImportBody, request: Request, admin: CurrentUser = Depends(guard), repo: Repository = Depends(get_repository)):
    _check_size(body)
    pack, report = _report(body)
    if not report["valid"]:
        details = [{"field": "pack", "issue": p} for p in report["problems"]] + [{"field": "tests", "issue": f"Missing hidden test definition: {k}"} for k in report["missing_tests"]]
        raise ApiError(422, "VALIDATION_ERROR", "The pack is not valid", details)
    courses, _t = await repo.tbl_select("courses", [("id", "eq", body.course_id)] if body.course_id else None, columns="id", order="created_at.asc", limit=1)
    if not courses:
        raise ApiError(404, "NOT_FOUND")
    course_id = courses[0]["id"]
    modules, _m = await repo.tbl_select("modules", [("course_id", "eq", course_id)], columns="id,module_number", order="sort_order.asc")
    if not modules:
        raise ApiError(422, "VALIDATION_ERROR", "The course has no module to put the lecture in")
    month = (pack.lecture_number - 1) // 8 + 1  # the course has eight lectures a month
    modules = [m for m in modules if m.get("module_number") == month] or modules
    lectures, _l = await repo.tbl_select("lectures", [("course_id", "eq", course_id)], columns="id,lecture_number,status")
    existing = {r["lecture_number"]: r for r in lectures}
    current = existing.get(pack.lecture_number)
    if current and current["status"] == "published" and not body.publish and not body.replace_published:
        raise ApiError(409, "CONFLICT", f"Lecture {pack.lecture_number} is published. Importing as a draft would hide it from learners; "
                       "publish the import, or confirm the replacement.")
    try:
        rows = build_rows(pack, body.tests, course_id=course_id, module_id=modules[0]["id"],
                          prerequisite_ids={n: r["id"] for n, r in existing.items()}, publish=body.publish)
    except PackError as exc:
        raise ApiError(422, "VALIDATION_ERROR", str(exc)) from exc
    for table in WRITE_ORDER:
        await repo.upsert_content(table, rows[table])
    lid = rows["lectures"][0]["id"]
    await audit.record(repo, request, admin.id, "admin.content_pack_imported", "lecture", lid,
                       {"lecture_id": lid, "lecture_number": pack.lecture_number, "course_id": course_id,
                        "published": body.publish, "count": sum(len(rows[t]) for t in WRITE_ORDER)})
    return {"lecture_id": lid, "lecture_number": pack.lecture_number, "status": "published" if body.publish else "draft",
            "created": current is None, "rows": {t: len(rows[t]) for t in WRITE_ORDER}}
