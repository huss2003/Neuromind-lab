import pytest

from app import auth, http


class Resp:
    def __init__(self, status, body):
        self.status_code, self._body = status, body

    def json(self):
        return self._body


@pytest.fixture
def stub(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://x.example")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "svc")
    auth._cache.clear()
    state = {"profile": {"role": "learner", "display_name": "A", "deactivated_at": None}}

    async def fake(method, url, **kw):
        if url.endswith("/auth/v1/user"):
            return Resp(200, {"id": "u1", "email": "a@x.test"})
        return Resp(200, [state["profile"]])

    monkeypatch.setattr(http, "request", fake)
    return state


@pytest.mark.anyio
async def test_deactivated_profile_is_refused_even_with_a_valid_token(stub):
    verifier = auth.SupabaseVerifier()
    assert (await verifier.verify("tok-1")).role == "learner"
    stub["profile"]["deactivated_at"] = "2026-10-14T00:00:00Z"
    auth._cache.clear()  # the cache window (30 s) is the documented delay before a deactivation reaches an active session
    with pytest.raises(Exception) as e:
        await verifier.verify("tok-1")
    assert getattr(e.value, "code", None) == "ACCOUNT_DEACTIVATED" and e.value.status_code == 403
