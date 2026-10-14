import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.auth import CurrentUser, get_verifier
from app.main import app
from app.repository import get_repository
from tests.fakes import InMemoryRepository


class FakeVerifier:
    users = {"learner-token": CurrentUser("u1", "learner"), "teacher-token": CurrentUser("u2", "teacher")}

    async def verify(self, token: str) -> CurrentUser:
        if token not in self.users:
            raise HTTPException(401)
        return self.users[token]


client = TestClient(app)


@pytest.fixture(autouse=True)
def _overrides():
    """Set per test (other test modules clear app.dependency_overrides); hermetic: no SUPABASE_* environment needed."""
    app.dependency_overrides[get_verifier] = FakeVerifier
    app.dependency_overrides[get_repository] = InMemoryRepository
    yield
    app.dependency_overrides.clear()


def auth(t):
    return {"Authorization": f"Bearer {t}"}


def test_me_requires_token():
    assert client.get("/api/v1/me").status_code == 401
    assert client.get("/api/v1/me", headers=auth("bad")).status_code == 401


def test_me_returns_verified_identity_ignoring_client_role():
    r = client.get("/api/v1/me", headers={**auth("learner-token"), "X-Role": "admin"})
    assert r.json()["id"] == "u1" and r.json()["role"] == "learner"


def test_teacher_route_guard():
    assert client.get("/api/v1/teacher/ping", headers=auth("learner-token")).status_code == 403
    assert client.get("/api/v1/teacher/ping", headers=auth("teacher-token")).status_code == 200
    assert client.get("/api/v1/teacher/ping", headers=auth("learner-token")).json()["error"]["code"] == "FORBIDDEN"
