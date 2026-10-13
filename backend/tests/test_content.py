import json

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.auth import CurrentUser, get_verifier
from app.main import app
from app.repository import get_repository
from app.services.manifest import ManifestError, build_segment

LID = "00000000-0000-4000-8000-000000000009"
CP = "00000000-0000-4000-8000-0000000000c1"


class FakeRepo:
    def __init__(self, segments=None):
        self.segments = segments if segments is not None else [
            {"id": "s1", "segment_order": 1, "segment_type": "video", "title": "v", "is_required": True,
             "media_provider": "external", "media_url": "http://x/v.mp4", "settings": {}},
            {"id": "s2", "segment_order": 2, "segment_type": "checkpoint", "title": "c", "is_required": True,
             "checkpoint_id": CP, "settings": {}},
            {"id": "s3", "segment_order": 3, "segment_type": "video", "title": "p", "is_required": True,
             "media_url": "http://x/p.mp4", "settings": {"on_end": {"type": "open_exercise", "exercise_id": "e1"}}},
        ]

    async def list_published_courses(self): return [{"id": "c1", "slug": "x", "title": "T", "description": ""}]
    async def get_published_course(self, i): return {"id": "c1", "slug": "x", "title": "T", "description": ""} if i == "00000000-0000-4000-8000-000000000001" else None
    async def list_published_lectures(self, c): return []
    async def get_published_lecture(self, i):
        return {"id": LID, "lecture_number": 9, "title": "L9", "summary": "", "learning_objectives": [],
                "duration_seconds": 3600, "content_version": 1} if i == LID else None
    async def list_segments(self, lecture_id): return self.segments
    async def get_checkpoint_with_question(self, c):
        # Even if a buggy repo leaked the key, the manifest model must not expose it.
        return {"id": CP, "checkpoint_type": "mcq", "required": True, "correct_option_id": "b",
                "question": {"id": "q1", "prompt": "P", "options": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}],
                             "correct_option_id": "b"}}


class FakeVerifier:
    async def verify(self, token):
        if token != "ok":
            raise HTTPException(401)
        return CurrentUser("u1", "learner")


def make_client(repo=None):
    app.dependency_overrides[get_verifier] = FakeVerifier
    app.dependency_overrides[get_repository] = lambda: repo or FakeRepo()
    return TestClient(app, raise_server_exceptions=False)


H = {"Authorization": "Bearer ok"}


def test_requires_auth():
    c = make_client()
    assert c.get("/api/v1/courses").status_code == 401
    assert c.get(f"/api/v1/lectures/{LID}").status_code == 401


def test_manifest_is_ordered_and_hides_answer_key():
    r = make_client().get(f"/api/v1/lectures/{LID}", headers=H)
    assert r.status_code == 200
    body = r.json()
    assert [s["order"] for s in body["segments"]] == [1, 2, 3]
    assert "correct" not in json.dumps(body).lower()
    assert body["segments"][1]["checkpoint"]["question"]["options"][0]["id"] == "a"
    assert body["segments"][2]["next_action"] == {"type": "open_exercise", "exercise_id": "e1"}


def test_unknown_or_malformed_lecture_is_404():
    c = make_client()
    assert c.get("/api/v1/lectures/00000000-0000-4000-8000-0000000000ff", headers=H).status_code == 404
    assert c.get("/api/v1/lectures/not-a-uuid", headers=H).status_code == 404


def test_missing_checkpoint_is_config_error_not_silent():
    repo = FakeRepo([{"id": "s2", "segment_order": 1, "segment_type": "checkpoint", "title": "c",
                      "is_required": True, "checkpoint_id": None, "settings": {}}])
    assert make_client(repo).get(f"/api/v1/lectures/{LID}", headers=H).status_code == 500


def test_exercise_segment_without_exercise_raises():
    try:
        build_segment({"id": "s", "segment_order": 1, "segment_type": "exercise", "title": "e",
                       "is_required": True, "settings": {}}, None)
    except ManifestError:
        return
    raise AssertionError("expected ManifestError")
