import pytest
from fastapi.testclient import TestClient

from app.auth import get_verifier
from app.auth_admin import get_auth_admin
from app.grader_client import get_grader
from app.main import app
from app.repository import get_repository
from tests.fakes import FakeAuthAdmin, FakeGrader, FakeVerifier, InMemoryRepository


@pytest.fixture
def env():
    repo, grader = InMemoryRepository(), FakeGrader()
    app.dependency_overrides[get_verifier] = FakeVerifier
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_grader] = lambda: grader
    client = TestClient(app, raise_server_exceptions=False)
    yield client, repo, grader
    app.dependency_overrides.clear()


def H(token="learner1", key=None):
    h = {"Authorization": f"Bearer {token}"}
    if key:
        h["Idempotency-Key"] = key
    return h


@pytest.fixture
def admin_env(env):
    """env plus a fake Supabase Auth admin; returns (client, repo, auth_admin)."""
    client, repo, _ = env
    fake = FakeAuthAdmin()
    app.dependency_overrides[get_auth_admin] = lambda: fake
    return client, repo, fake
