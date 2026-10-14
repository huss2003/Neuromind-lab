"""Data access boundary. Services depend on the `Repository` protocol; production uses
PostgREST with the server-only service-role key (bypasses RLS, so every query filters
explicitly); tests use an in-memory implementation (tests/fakes.py)."""
import copy
import functools
import os
import time
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

import httpx

from app import http

Row = dict[str, Any]


_CONTENT_TTL = float(os.getenv("CONTENT_CACHE_SECONDS", "15"))
_content_cache: dict[tuple, tuple[float, Any]] = {}


def cached_content(fn):
    """Short in-process cache for PUBLISHED, learner-independent content (courses, lectures, segments, exercises).
    Access control is still checked per request; learner state is never cached. A republish shows up within CONTENT_CACHE_SECONDS."""
    @functools.wraps(fn)
    async def wrapper(self, *args):
        key = (fn.__name__, args)
        hit = _content_cache.get(key)
        now = time.monotonic()
        if _CONTENT_TTL > 0 and hit and now - hit[0] < _CONTENT_TTL:
            return copy.deepcopy(hit[1])
        value = await fn(self, *args)
        if _CONTENT_TTL > 0:
            if len(_content_cache) > 500:
                _content_cache.clear()
            _content_cache[key] = (now, copy.deepcopy(value))
        return value
    return wrapper


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
    async def claim_next_submission(self, worker_id: str, lease_seconds: int, max_claims: int) -> Row | None: ...
    async def extend_lease(self, submission_id: str, worker_id: str, lease_seconds: int) -> bool: ...
    async def release_submission(self, submission_id: str, worker_id: str) -> bool: ...
    async def queue_stats(self) -> Row: ...
    async def recompute_progress(self, learner_id: str, course_id: str) -> Row: ...
    # --- v1.0 additions ---
    async def list_published_modules(self, course_id: str) -> list[Row]: ...
    async def insert_audit(self, row: Row) -> None: ...
    async def list_hint_reveals(self, learner_id: str, exercise_id: str, attempt_number: int) -> list[Row]: ...
    async def insert_hint_reveal(self, row: Row) -> Row: ...
    async def get_draft(self, learner_id: str, exercise_id: str) -> Row | None: ...
    async def upsert_draft(self, learner_id: str, exercise_id: str, source_code: str, content_version: int | None = None) -> None: ...
    async def submission_load(self, learner_id: str, since_iso: str) -> tuple[int, int]: ...  # (recent, in-flight)
    async def list_assigned_learner_ids(self, teacher_id: str) -> list[str]: ...
    async def list_learners_page(self, ids: list[str] | None, q: str | None, limit: int, offset: int) -> tuple[list[Row], int]: ...
    async def titles(self, lecture_ids: list[str], checkpoint_ids: list[str], exercise_ids: list[str]) -> dict[str, dict[str, str]]: ...
    async def insert_feedback(self, row: Row) -> Row: ...
    async def list_feedback(self, learner_id: str, published_only: bool) -> list[Row]: ...
    async def ping(self) -> bool: ...
    # --- flow v1.0 ---
    async def list_enrolled_course_ids(self, learner_id: str) -> list[str]: ...
    async def list_exercises_basic(self, ids: list[str]) -> list[Row]: ...
    async def list_all_lectures(self) -> list[Row]: ...
    async def set_role(self, user_id: str, role: str) -> str | None: ...  # returns previous role
    async def upsert_enrollment(self, learner_id: str, course_id: str) -> None: ...
    async def revoke_enrollment(self, learner_id: str, course_id: str) -> None: ...
    async def upsert_assignment(self, teacher_id: str, learner_id: str, course_id: str) -> None: ...
    async def revoke_assignment(self, teacher_id: str, learner_id: str, course_id: str) -> None: ...
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
        return await http.request(method, f"{self.url}/{table}", params=params, json=json, headers=headers)

    async def _get(self, table: str, **params: str) -> list[Row]:
        r = await self._req("GET", table, params)
        r.raise_for_status()
        return r.json()

    async def _one(self, table: str, **params: str) -> Row | None:
        rows = await self._get(table, **params)
        return rows[0] if rows else None

    # content
    @cached_content
    async def list_published_courses(self):
        return await self._get("courses", status="eq.published", select="id,slug,title,description", order="created_at")

    async def get_published_course(self, course_id):
        return await self._one("courses", id=f"eq.{course_id}", status="eq.published", select="id,slug,title,description")

    @cached_content
    async def list_published_lectures(self, course_id):
        return await self._get(
            "lectures", course_id=f"eq.{course_id}", status="eq.published",
            select="id,module_id,lecture_number,title,summary,duration_seconds,prerequisites", order="lecture_number")

    @cached_content
    async def get_published_lecture(self, lecture_id):
        return await self._one("lectures", id=f"eq.{lecture_id}", status="eq.published", select="*")

    @cached_content
    async def list_segments(self, lecture_id):
        return await self._get("lecture_segments", lecture_id=f"eq.{lecture_id}", select="*", order="segment_order")

    async def get_checkpoint_with_question(self, checkpoint_id):
        return await self._one(
            "lecture_checkpoints", id=f"eq.{checkpoint_id}",
            select="id,checkpoint_type,required,question:mcq_questions(id,prompt,options,shuffle_options)")

    async def get_checkpoint(self, checkpoint_id):
        return await self._one("lecture_checkpoints", id=f"eq.{checkpoint_id}", select="*")

    async def get_question_full(self, question_id):
        return await self._one("mcq_questions", id=f"eq.{question_id}", select="*")

    @cached_content
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

    async def claim_next_submission(self, worker_id, lease_seconds, max_claims):
        r = await self._req("POST", "rpc/claim_next_submission",
                            json={"p_worker": worker_id, "p_lease_seconds": lease_seconds, "p_max_claims": max_claims})
        r.raise_for_status()
        rows = r.json()
        return rows[0] if rows else None

    async def extend_lease(self, submission_id, worker_id, lease_seconds):
        until = (datetime.now(UTC) + timedelta(seconds=lease_seconds)).isoformat()
        r = await self._req("PATCH", "lab_submissions",
                            {"id": f"eq.{submission_id}", "claimed_by": f"eq.{worker_id}", "status": "eq.running"},
                            json={"lease_expires_at": until}, prefer="return=representation")
        r.raise_for_status()
        return bool(r.json())

    async def release_submission(self, submission_id, worker_id):
        r = await self._req("PATCH", "lab_submissions",
                            {"id": f"eq.{submission_id}", "claimed_by": f"eq.{worker_id}", "status": "eq.running"},
                            json={"status": "queued", "claimed_by": None, "lease_expires_at": None},
                            prefer="return=representation")
        r.raise_for_status()
        return bool(r.json())

    async def queue_stats(self):
        waiting = await self._get("lab_submissions", status="eq.queued", select="created_at", order="created_at.asc", limit="500")
        running = await self._get("lab_submissions", status="eq.running", select="id", limit="500")
        oldest = None
        if waiting:
            created = datetime.fromisoformat(str(waiting[0]["created_at"]).replace("Z", "+00:00"))
            oldest = max(0, int((datetime.now(UTC) - created).total_seconds()))
        return {"queued": len(waiting), "running": len(running), "oldest_queued_seconds": oldest}

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

    # flow v1.0
    async def list_enrolled_course_ids(self, learner_id):
        rows = await self._get("enrollments", learner_id=f"eq.{learner_id}", revoked_at="is.null", select="course_id")
        return [r["course_id"] for r in rows]

    async def list_exercises_basic(self, ids):
        if not ids:
            return []
        return await self._get("lecture_exercises", id=_in(ids), select="id,title,lecture_id")

    async def list_all_lectures(self):
        return await self._get("lectures", select="id,lecture_number,title,status,content_version,published_at", order="lecture_number")

    async def set_role(self, user_id, role):
        prev = await self._one("profiles", id=f"eq.{user_id}", select="role")
        if not prev:
            return None
        r = await self._req("PATCH", "profiles", {"id": f"eq.{user_id}"}, json={"role": role})
        r.raise_for_status()
        return prev["role"]

    async def upsert_enrollment(self, learner_id, course_id):
        r = await self._req("POST", "enrollments", {"on_conflict": "learner_id,course_id"},
                            json={"learner_id": learner_id, "course_id": course_id, "revoked_at": None},
                            prefer="resolution=merge-duplicates")
        r.raise_for_status()

    async def revoke_enrollment(self, learner_id, course_id):
        from datetime import UTC, datetime
        r = await self._req("PATCH", "enrollments", {"learner_id": f"eq.{learner_id}", "course_id": f"eq.{course_id}"},
                            json={"revoked_at": datetime.now(UTC).isoformat()})
        r.raise_for_status()

    async def upsert_assignment(self, teacher_id, learner_id, course_id):
        r = await self._req("POST", "teacher_assignments", {"on_conflict": "teacher_id,learner_id,course_id"},
                            json={"teacher_id": teacher_id, "learner_id": learner_id, "course_id": course_id, "revoked_at": None},
                            prefer="resolution=merge-duplicates")
        r.raise_for_status()

    async def revoke_assignment(self, teacher_id, learner_id, course_id):
        from datetime import UTC, datetime
        r = await self._req("PATCH", "teacher_assignments", {"teacher_id": f"eq.{teacher_id}", "learner_id": f"eq.{learner_id}",
                                                              "course_id": f"eq.{course_id}"},
                            json={"revoked_at": datetime.now(UTC).isoformat()})
        r.raise_for_status()

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
    @cached_content
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

    async def upsert_draft(self, learner_id, exercise_id, source_code, content_version=None):
        from datetime import UTC, datetime
        r = await self._req("POST", "lab_drafts", {"on_conflict": "learner_id,exercise_id"}, json={
            "learner_id": learner_id, "exercise_id": exercise_id, "source_code": source_code,
            "content_version": content_version, "updated_at": datetime.now(UTC).isoformat()}, prefer="resolution=merge-duplicates")
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
