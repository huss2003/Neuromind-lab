import pytest

from app import repository as r


class Stub:
    def __init__(self):
        self.calls = 0

    @r.cached_content
    async def rows(self, key):
        self.calls += 1
        return [{"id": key, "n": self.calls}]


@pytest.fixture(autouse=True)
def _ttl(monkeypatch):
    monkeypatch.setattr(r, "_CONTENT_TTL", 15.0)
    r._content_cache.clear()
    yield
    r._content_cache.clear()


@pytest.mark.anyio
async def test_second_read_is_served_from_cache_and_callers_cannot_corrupt_it():
    s = Stub()
    first = await s.rows("a")
    first[0]["id"] = "mutated"
    second = await s.rows("a")
    assert s.calls == 1 and second[0]["id"] == "a"
    await s.rows("b")
    assert s.calls == 2


@pytest.mark.anyio
async def test_expiry_and_disabled_cache_hit_the_database(monkeypatch):
    s = Stub()
    clock = [100.0]
    monkeypatch.setattr(r.time, "monotonic", lambda: clock[0])
    await s.rows("a")
    clock[0] += 16
    await s.rows("a")
    assert s.calls == 2
    monkeypatch.setattr(r, "_CONTENT_TTL", 0.0)
    await s.rows("a")
    await s.rows("a")
    assert s.calls == 4
