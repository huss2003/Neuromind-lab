"""Data access boundary. Services depend on the `Repository` protocol; production uses
PostgREST with the server-only service-role key (bypasses RLS, so every query filters
explicitly); tests use an in-memory implementation (tests/fakes.py)."""
import os
from typing import Any, Protocol

import httpx

Row = dict[str, Any]


class Repository(Protocol):
    # --- content (published, learner-safe selects) ---
    async def list_published_courses(self) -> list[Row]: ...
    async def get_published_course(self, course_id: str) -> Row | None: ...
    async def list_published_lectures(self, course_id: str) -> list[Row]: ...
    async def get_published_lecture(self, lecture_id: str) -> Row | None: ...
    async def list_segments(self, lecture_id: str) -> list[Row]: ...
    async def get_checkpoint_with_question(self, checkpoint_id: str) -> Row | None: ...
    # --- server-only content ---
    async def get_checkpoint(self, checkpoint_id: str) -> Row | None: ...
    async def get_question_full(self, question_id: str) -> Row | None: ...
    async def get_published_exercise(self, exercise_id: str) -> Row | None: ...
    async def list_exercise_tests(self, exercise_id: str) -> list[Row]: ...
    # --- learner state ---
    async def get_session(self, learner_id: str, lecture_id: str) -> Row | None: ...
    async def create_session(self, learner_id: str, lecture_id: str, first_segment_id: str | None) -> Row: ...
    async def update_session(self, session_id: str, expected_version: int | None, fields: Row) -> Row | None: ...
    async def list_attempts(self, learner_id: str, checkpoint_ids: list[str]) -> list[Row]: ...
    async def find_attempt_by_key(self, learner_id: str, key: str) -> Row | None: ...
    async def insert_attempt(self, row: Row) -> Row: ...
    async def list_submissions(self, learner_id: str, exercise_ids: list[str]) -> list[Row]: ...
    async def get_submission(self, submission_id: str) -> Row | None: ...
    async def find_submission_by_key(self, learner_id: str, key: str) -> Row | None: ...
    async def insert_submission(self, row: Row) -> Row: ...
    async def update_submission(self, submission_id: str, fields: Row) -> Row | None: ...
    async def recompute_progress(self, learner_id: str, course_id: str) -> Row: ...
    # --- v1.0 additions ---
    async def list_published_modules(self, course_id: str) -> list[Row]: ...
    async def insert_audit(self, row: Row) -> None: ...
    async def list_hint_reveals(self, learner_id: str, exercise_id: str, attempt_number: int) -> list[Row]: ...
    async def insert_hint_reveal(self, row: Row) -> Row: ...
    async def get_draft(self, learner_id: str, exercise_id: str) -> Row | None: ...
    async def upsert_draft(self, learner_id: str, exercise_id: str, source_code: str) -> None: ...
    async def submission_load(self, learner_id: str, since_iso: str) -> tuple[int, int]: ...  # (recent, in-flight)
    async def list_assigned_learner_ids(self, teacher_id: str) -> list[str]: ...
    async def list_learners_page(self, ids: list[str] | None, q: str | None, limit: int, offset: int) -> tuple[list[Row], int]: ...
    async def titles(self, lecture_ids: list[str], checkpoint_ids: list[str], exercise_ids: list[str]) -> dict[str, dict[str, str]]: ...
    async def insert_feedback(self, row: Row) -> Row: ...
    async def list_feedback(self, learner_id: str, published_only: bool) -> list[Row]: ...
    async def ping(self) -> bool: ...
    # --- teacher ---
    async def list_learners(self) -> list[Row]: ...
    async def get_profile(self, user_id: str) -> Row | None: ...
    async def list_learner_sessions(self, learner_id: str) -> list[Row]: ...
    async def list_learner_attempts(self, learner_id: str) -> list[Row]: ...
    async def list_learner_submissions(self, learner_id: str) -> list[Row]: ...


def _in(values: list[str]) -> str:
    return "in.(" + ",".join(values) + ")"


class PostgrestRepository:
    def __init__(self) -> None:
        self.url = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1"
        key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
        self.headers = {"apikey": key, "Authorization": f"Bearer {key}"}

    async def _req(self, method: str, table: str, params: dict[str, str] | None = None,
                   json: Any = None, prefer: str | None = None) -> httpx.Response:
        headers = dict(self.headers)
        if prefer:
            headers["Prefer"] = prefer
        async with httpx.AsyncClient(timeout=8) as c:
            return await c.request(method, f"{self.url}/{table}", params=params, json=json, headers=headers)

    async def _get(self, table: str, **params: str) -> list[Row]:
        r = await self._req("GET", table, params)
        r.raise_for_status()
        return r.json()

    async def _one(self, table: str, **params: str) -> Row | None:
        rows = await self._get(table, **params)
        return rows[0] if rows else None

    # content
    async def list_published_courses(self):
        return await self._get("courses", status="eq.published", select="id,slug,title,description", order="created_at")

    async def get_published_course(self, course_id):
        return await self._one("courses", id=f"eq.{course_id}", status="eq.published", select="id,slug,title,description")

    async def list_published_lectures(self, course_id):
        return await self._get(
            "lectures", course_id=f"eq.{course_id}", status="eq.published",
            select="id,module_id,lecture_number,title,summary,duration_seconds", order="lecture_number")

    async def get_published_lecture(self, lecture_id):
        return await self._one("lectures", id=f"eq.{lecture_id}", status="eq.published", select="*")

    async def list_segments(self, lecture_id):
        return await self._get("lecture_segments", lecture_id=f"eq.{lecture_id}", select="*", order="segment_order")

    async def get_checkpoint_with_question(self, checkpoint_id):
        return await self._one(
            "lecture_checkpoints", id=f"eq.{checkpoint_id}",
            select="id,checkpoint_type,required,question:mcq_questions(id,prompt,options)")

    async def get_checkpoint(self, checkpoint_id):
        return await self._one("lecture_checkpoints", id=f"eq.{checkpoint_id}", select="*")

    async def get_question_full(self, question_id):
        return await self._one("mcq_questions", id=f"eq.{question_id}", select="*")

    async def get_published_exercise(self, exercise_id):
        return await self._one("lecture_exercises", id=f"eq.{exercise_id}", status="eq.published", select="*")

    async def list_exercise_tests(self, exercise_id):
        return await self._get("exercise_tests", exercise_id=f"eq.{exercise_id}", select="*", order="test_order")

    # learner state
    async def get_session(self, learner_id, lecture_id):
        return await self._one("lecture_sessions", learner_id=f"eq.{learner_id}", lecture_id=f"eq.{lecture_id}", select="*")

    async def create_session(self, learner_id, lecture_id, first_segment_id):
        r = await self._req("POST", "lecture_sessions", json={
            "learner_id": learner_id, "lecture_id": lecture_id, "current_segment_id": first_segment_id,
            "status": "in_progress"}, prefer="return=representation")
        if r.status_code == 409:  # concurrent create: unique(learner_id, lecture_id)
            existing = await self.get_session(learner_id, lecture_id)
            assert existing is not None
            return existing
        r.raise_for_status()
        return r.json()[0]

    async def update_session(self, session_id, expected_version, fields):
        params = {"id": f"eq.{session_id}"}
        if expected_version is not None:
            params["state_version"] = f"eq.{expected_version}"
            fields = {**fields, "state_version": expected_version + 1}
        r = await self._req("PATCH", "lecture_sessions", params, json=fields, prefer="return=representation")
        r.raise_for_status()
        rows = r.json()
        return rows[0] if rows else None

    async def list_attempts(self, learner_id, checkpoint_ids):
        if not checkpoint_ids:
            return []
        return await self._get("checkpoint_attempts", learner_id=f"eq.{learner_id}",
                               checkpoint_id=_in(checkpoint_ids), select="*", order="submitted_at")

    async def find_attempt_by_key(self, learner_id, key):
        return await self._one("checkpoint_attempts", learner_id=f"eq.{learner_id}", idempotency_key=f"eq.{key}", select="*")

    async def insert_attempt(self, row):
        r = await self._req("POST", "checkpoint_attempts", json=row, prefer="return=representation")
        if r.status_code == 409:
            existing = await self.find_attempt_by_key(row["learner_id"], row["idempotency_key"])
            assert existing is not None
            return existing
        r.raise_for_status()
        return r.json()[0]

    async def list_submissions(self, learner_id, exercise_ids):
        if not exercise_ids:
            return []
        return await self._get("lab_submissions", learner_id=f"eq.{learner_id}",
                               exercise_id=_in(exercise_ids), select="*", order="created_at")

    async def get_submission(self, submission_id):
        return await self._one("lab_submissions", id=f"eq.{submission_id}", select="*")

    async def find_submission_by_key(self, learner_id, key):
        return await self._one("lab_submissions", learner_id=f"eq.{learner_id}", idempotency_key=f"eq.{key}", select="*")

    async def insert_submission(self, row):
        for _ in range(3):  # submission_number race: retry with the next number
            existing = await self._get("lab_submissions", learner_id=f"eq.{row['learner_id']}",
                                       exercise_id=f"eq.{row['exercise_id']}", select="submission_number",
                                       order="submission_number.desc", limit="1")
            number = (existing[0]["submission_number"] + 1) if existing else 1
            r = await self._req("POST", "lab_submissions", json={**row, "submission_number": number},
                                prefer="return=representation")
            if r.status_code == 409:
                dup = await self.find_submission_by_key(row["learner_id"], row["idempotency_key"])
                if dup:
                    return dup
                continue
            r.raise_for_status()
            return r.json()[0]
        raise RuntimeError("could not allocate submission number")

    async def update_submission(self, submission_id, fields):
        r = await self._req("PATCH", "lab_submissions", {"id": f"eq.{submission_id}"}, json=fields,
                            prefer="return=representation")
        r.raise_for_status()
        rows = r.json()
        return rows[0] if rows else None

    async def recompute_progress(self, learner_id, course_id):
        lectures = await self._get("lectures", course_id=f"eq.{course_id}", status="eq.published", select="id")
        ids = [x["id"] for x in lectures]
        done = 0
        if ids:
            done = len(await self._get("lecture_sessions", learner_id=f"eq.{learner_id}",
                                       lecture_id=_in(ids), status="eq.completed", select="id"))
        total = len(ids)
        row = {"learner_id": learner_id, "course_id": course_id, "completed_lectures": done,
               "total_lectures": total, "progress_percent": round(100 * done / total, 2) if total else 0}
        r = await self._req("POST", "student_progress", {"on_conflict": "learner_id,course_id"}, json=row,
                            prefer="resolution=merge-duplicates,return=representation")
        r.raise_for_status()
        return r.json()[0]

    # teacher
    async def list_learners(self):
        return await self._get("profiles", role="eq.learner", select="id,display_name,created_at", order="created_at")

    async def get_profile(self, user_id):
        return await self._one("profiles", id=f"eq.{user_id}", select="id,display_name,role")

    async def list_learner_sessions(self, learner_id):
        return await self._get("lecture_sessions", learner_id=f"eq.{learner_id}", select="*")

    async def list_learner_attempts(self, learner_id):
        return await self._get("checkpoint_attempts", learner_id=f"eq.{learner_id}", select="*", order="submitted_at")

    async def list_learner_submissions(self, learner_id):
        return await self._get("lab_submissions", learner_id=f"eq.{learner_id}", select="*", order="created_at")

    # v1.0 additions
    async def list_published_modules(self, course_id):
        return await self._get("modules", course_id=f"eq.{course_id}", status="eq.published",
                               select="id,module_number,title,description,sort_order", order="sort_order")

    async def insert_audit(self, row):
        r = await self._req("POST", "audit_logs", json=row)
        r.raise_for_status()

    async def list_hint_reveals(self, learner_id, exercise_id, attempt_number):
        return await self._get("exercise_hint_reveals", learner_id=f"eq.{learner_id}", exercise_id=f"eq.{exercise_id}",
                               attempt_number=f"eq.{attempt_number}", select="*", order="hint_index")

    async def insert_hint_reveal(self, row):
        r = await self._req("POST", "exercise_hint_reveals", json=row, prefer="return=representation")
        if r.status_code == 409:
            rows = await self.list_hint_reveals(row["learner_id"], row["exercise_id"], row["attempt_number"])
            return next(x for x in rows if x["hint_index"] == row["hint_index"])
        r.raise_for_status()
        return r.json()[0]

    async def get_draft(self, learner_id, exercise_id):
        return await self._one("lab_drafts", learner_id=f"eq.{learner_id}", exercise_id=f"eq.{exercise_id}", select="*")

    async def upsert_draft(self, learner_id, exercise_id, source_code):
        from datetime import UTC, datetime
        r = await self._req("POST", "lab_drafts", {"on_conflict": "learner_id,exercise_id"}, json={
            "learner_id": learner_id, "exercise_id": exercise_id, "source_code": source_code,
            "updated_at": datetime.now(UTC).isoformat()}, prefer="resolution=merge-duplicates")
        r.raise_for_status()

    async def submission_load(self, learner_id, since_iso):
        recent = await self._get("lab_submissions", learner_id=f"eq.{learner_id}", created_at=f"gte.{since_iso}", select="id")
        inflight = await self._get("lab_submissions", learner_id=f"eq.{learner_id}", status="in.(queued,running)", select="id")
        return len(recent), len(inflight)

    async def list_assigned_learner_ids(self, teacher_id):
        rows = await self._get("teacher_assignments", teacher_id=f"eq.{teacher_id}", revoked_at="is.null", select="learner_id")
        return sorted({r["learner_id"] for r in rows})

    async def list_learners_page(self, ids, q, limit, offset):
        if ids is not None and not ids:
            return [], 0
        params = {"role": "eq.learner", "select": "id,display_name,created_at", "order": "display_name,created_at",
                  "limit": str(limit), "offset": str(offset)}
        if ids is not None:
            params["id"] = _in(ids)
        if q:
            safe = "".join(ch for ch in q if ch.isalnum() or ch in " ._-")[:50]
            if safe:
                params["display_name"] = f"ilike.*{safe}*"
        r = await self._req("GET", "profiles", params, prefer="count=exact")
        r.raise_for_status()
        total = int(r.headers.get("content-range", "0-0/0").split("/")[-1] or 0)
        return r.json(), total

    async def titles(self, lecture_ids, checkpoint_ids, exercise_ids):
        out: dict[str, dict[str, str]] = {"lectures": {}, "checkpoints": {}, "exercises": {}}
        if lecture_ids:
            for r in await self._get("lectures", id=_in(lecture_ids), select="id,title,lecture_number"):
                out["lectures"][r["id"]] = f"Lecture {r['lecture_number']}: {r['title']}"
        if checkpoint_ids:
            for r in await self._get("lecture_segments", checkpoint_id=_in(checkpoint_ids), select="checkpoint_id,title"):
                out["checkpoints"][r["checkpoint_id"]] = r["title"]
        if exercise_ids:
            for r in await self._get("lecture_exercises", id=_in(exercise_ids), select="id,title"):
                out["exercises"][r["id"]] = r["title"]
        return out

    async def insert_feedback(self, row):
        r = await self._req("POST", "teacher_feedback", json=row, prefer="return=representation")
        r.raise_for_status()
        return r.json()[0]

    async def list_feedback(self, learner_id, published_only):
        params = {"learner_id": f"eq.{learner_id}", "select": "*", "order": "created_at.desc"}
        if published_only:
            params["published"] = "eq.true"
        r = await self._req("GET", "teacher_feedback", params)
        r.raise_for_status()
        return r.json()

    async def ping(self):
        try:
            r = await self._req("GET", "courses", {"select": "id", "limit": "1"})
            return r.status_code == 200
        except httpx.HTTPError:
            return False


def get_repository() -> Repository:
    return PostgrestRepository()


# Back-compat alias used by the content router.
ContentRepository = Repository
