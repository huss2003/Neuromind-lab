from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok_with_request_id():
    r = client.get("/api/v1/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    assert r.headers["X-Request-ID"]


def test_not_found_uses_error_shape():
    r = client.get("/api/v1/nope")
    assert r.status_code == 404
    err = r.json()["error"]
    assert err["code"] == "NOT_FOUND" and err["request_id"]
