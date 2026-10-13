"""Data access boundary. Services depend on `ContentRepository`; production uses PostgREST
with the server-only service-role key, tests use an in-memory fake."""
import os
from typing import Any, Protocol

import httpx


class ContentRepository(Protocol):
    async def list_published_courses(self) -> list[dict[str, Any]]: ...
    async def get_published_course(self, course_id: str) -> dict[str, Any] | None: ...
    async def list_published_lectures(self, course_id: str) -> list[dict[str, Any]]: ...
    async def get_published_lecture(self, lecture_id: str) -> dict[str, Any] | None: ...
    async def list_segments(self, lecture_id: str) -> list[dict[str, Any]]: ...
    async def get_checkpoint_with_question(self, checkpoint_id: str) -> dict[str, Any] | None: ...


class PostgrestRepository:
    """Uses the service-role key: it bypasses RLS, so every query here must filter explicitly."""

    def __init__(self) -> None:
        self.url = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1"
        key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
        self.headers = {"apikey": key, "Authorization": f"Bearer {key}"}

    async def _get(self, table: str, **params: str) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{self.url}/{table}", params=params, headers=self.headers)
        r.raise_for_status()
        return r.json()

    async def list_published_courses(self):
        return await self._get("courses", status="eq.published", select="id,slug,title,description", order="created_at")

    async def get_published_course(self, course_id):
        rows = await self._get("courses", id=f"eq.{course_id}", status="eq.published", select="id,slug,title,description")
        return rows[0] if rows else None

    async def list_published_lectures(self, course_id):
        return await self._get(
            "lectures", course_id=f"eq.{course_id}", status="eq.published",
            select="id,module_id,lecture_number,title,summary,duration_seconds", order="lecture_number",
        )

    async def get_published_lecture(self, lecture_id):
        rows = await self._get("lectures", id=f"eq.{lecture_id}", status="eq.published", select="*")
        return rows[0] if rows else None

    async def list_segments(self, lecture_id):
        return await self._get("lecture_segments", lecture_id=f"eq.{lecture_id}", select="*", order="segment_order")

    async def get_checkpoint_with_question(self, checkpoint_id):
        rows = await self._get(
            "lecture_checkpoints", id=f"eq.{checkpoint_id}",
            select="id,checkpoint_type,required,question:mcq_questions(id,prompt,options)",
        )
        return rows[0] if rows else None


def get_repository() -> ContentRepository:
    return PostgrestRepository()
