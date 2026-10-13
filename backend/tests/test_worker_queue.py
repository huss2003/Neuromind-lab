"""Durable grading queue: claim/lease/retry/dead-letter/idempotent result (Phase 3). Runs against the in-memory repository
that mirrors the SQL in 0006; the SQL itself still needs a live-database test (see PRODUCTION_READINESS_REPORT)."""
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from tests.conftest import H
from tests.fakes import CP1, CP2, EX, Q1, Q2
from tests.test_flow import answer

W = {"X-Worker-Token": "test-worker-token"}
BASE = "/api/v1/internal/grader"
GOOD = {"status": "passed", "passed_tests": 2, "total_tests": 2, "score": 100, "execution_ms": 12,
        "feedback": [{"kind": "success", "message": "ok"}],
        "criteria": [{"test_order": 1, "passed": True}, {"test_order": 2, "passed": True}], "grader_version": "1.1.0"}


@pytest.fixture(autouse=True)
def queue_mode(monkeypatch):
    monkeypatch.setenv("GRADER_MODE", "queue")
    monkeypatch.setenv("GRADER_WORKER_TOKEN", "test-worker-token")


def submit(c, code="GOOD", token="learner1"):
    answer(c, CP1, Q1, "b")
    answer(c, CP2, Q2, "a")
    r = c.post(f"/api/v1/exercises/{EX}/submissions", headers=H(token, str(uuid.uuid4())), json={"source_code": code})
    assert r.status_code == 202
    return r.json()["submission_id"]


def claim(c, worker="w-1"):
    return c.post(f"{BASE}/claim", headers=W, json={"worker_id": worker})


def test_api_does_not_grade_in_queue_mode_and_submission_waits_as_queued(env):
    c, repo, grader = env
    sid = submit(c)
    assert grader.calls == []
    assert c.get(f"/api/v1/submissions/{sid}", headers=H()).json()["status"] == "queued"


def test_worker_claims_grades_and_result_is_final_and_idempotent(env):
    c, repo, _ = env
    sid = submit(c)
    job = claim(c).json()
    assert job["submission_id"] == sid and job["source_code"] == "GOOD" and len(job["tests"]) == 2
    assert c.get(f"/api/v1/submissions/{sid}", headers=H()).json()["status"] == "running"
    r = c.post(f"{BASE}/jobs/{sid}/result", headers=W, json={"worker_id": "w-1", "result": GOOD})
    assert r.json() == {"accepted": True}
    done = c.get(f"/api/v1/submissions/{sid}", headers=H()).json()
    assert done["status"] == "passed" and done["score"] == 100
    again = c.post(f"{BASE}/jobs/{sid}/result", headers=W, json={"worker_id": "w-1", "result": {**GOOD, "score": 5, "status": "failed"}})
    assert again.status_code == 200 and again.json()["accepted"] is False
    assert c.get(f"/api/v1/submissions/{sid}", headers=H()).json()["score"] == 100  # a duplicate/late result cannot change it
    assert len([a for a in repo.audit if a["event_type"] == "submission.finished"]) == 1


def test_empty_queue_returns_204_and_two_workers_never_get_the_same_job(env):
    c, _, _ = env
    assert claim(c).status_code == 204
    submit(c)
    assert claim(c, "w-1").status_code == 200
    assert claim(c, "w-2").status_code == 204


def test_expired_lease_is_reclaimed_by_another_worker_and_old_worker_is_fenced_out(env):
    c, repo, _ = env
    sid = submit(c)
    claim(c, "w-1")
    next(s for s in repo.submissions if s["id"] == sid)["lease_expires_at"] = datetime.now(UTC) - timedelta(seconds=1)
    assert claim(c, "w-2").json()["claim_count"] == 2
    stale = c.post(f"{BASE}/jobs/{sid}/result", headers=W, json={"worker_id": "w-1", "result": GOOD})
    assert stale.status_code == 409 and "LEASE_LOST" in stale.text
    ok = c.post(f"{BASE}/jobs/{sid}/result", headers=W, json={"worker_id": "w-2", "result": GOOD})
    assert ok.json()["accepted"] is True


def test_job_that_keeps_losing_its_worker_is_dead_lettered_as_a_system_error_not_a_learner_failure(env):
    c, repo, _ = env
    sid = submit(c)
    sub = next(s for s in repo.submissions if s["id"] == sid)
    for n in range(3):
        assert claim(c, f"w-{n}").status_code == 200
        sub["lease_expires_at"] = datetime.now(UTC) - timedelta(seconds=1)
    assert claim(c, "w-9").status_code == 204
    view = c.get(f"/api/v1/submissions/{sid}", headers=H()).json()
    assert view["status"] == "error" and view["infrastructure_error"] is True and view["score"] is None


def test_release_puts_job_back_and_heartbeat_extends_lease(env):
    c, repo, _ = env
    sid = submit(c)
    claim(c, "w-1")
    assert c.post(f"{BASE}/jobs/{sid}/heartbeat", headers=W, json={"worker_id": "w-1"}).status_code == 200
    assert c.post(f"{BASE}/jobs/{sid}/heartbeat", headers=W, json={"worker_id": "w-2"}).status_code == 409
    assert c.post(f"{BASE}/jobs/{sid}/release", headers=W, json={"worker_id": "w-1"}).json() == {"released": True}
    assert c.get(f"/api/v1/submissions/{sid}", headers=H()).json()["status"] == "queued"


def test_malformed_or_forged_worker_result_is_a_system_error_never_a_pass(env):
    c, _, _ = env
    sid = submit(c)
    claim(c)
    r = c.post(f"{BASE}/jobs/{sid}/result", headers=W, json={"worker_id": "w-1", "result": {"status": "passed", "score": 1000}})
    assert r.status_code == 200
    view = c.get(f"/api/v1/submissions/{sid}", headers=H()).json()
    assert view["status"] == "error" and view["score"] is None


def test_worker_interface_requires_the_worker_token_and_users_cannot_use_it(env):
    c, _, _ = env
    submit(c)
    assert c.post(f"{BASE}/claim", json={"worker_id": "w-1"}).status_code == 401
    assert c.post(f"{BASE}/claim", headers={"X-Worker-Token": "nope"}, json={"worker_id": "w-1"}).status_code == 401
    assert c.post(f"{BASE}/claim", headers=H("learner1"), json={"worker_id": "w-1"}).status_code == 401
    assert c.post(f"{BASE}/claim", headers=H("admin"), json={"worker_id": "w-1"}).status_code == 401


def test_worker_interface_is_disabled_without_a_configured_token(env, monkeypatch):
    c, _, _ = env
    monkeypatch.delenv("GRADER_WORKER_TOKEN")
    assert c.post(f"{BASE}/claim", headers=W, json={"worker_id": "w-1"}).status_code == 503


def test_unowned_result_is_rejected(env):
    c, _, _ = env
    sid = submit(c)
    assert c.post(f"{BASE}/jobs/{sid}/result", headers=W, json={"worker_id": "w-1", "result": GOOD}).status_code == 409  # never claimed


def test_hint_penalty_is_applied_by_the_server_to_the_current_attempt_only(env):
    c, _, _ = env
    answer(c, CP1, Q1, "b")
    answer(c, CP2, Q2, "a")
    assert c.post(f"/api/v1/exercises/{EX}/hints", headers=H(), json={"hint_index": 0}).status_code == 200
    sid = c.post(f"/api/v1/exercises/{EX}/submissions", headers=H("learner1", str(uuid.uuid4())), json={"source_code": "GOOD"}).json()["submission_id"]
    claim(c)
    c.post(f"{BASE}/jobs/{sid}/result", headers=W, json={"worker_id": "w-1", "result": GOOD})
    view = c.get(f"/api/v1/submissions/{sid}", headers=H()).json()
    assert view["raw_score"] == 100 and view["score"] == 90 and view["hints_used"] == 1


def test_worker_claim_payload_contains_tests_but_user_endpoints_never_do(env):
    c, _, _ = env
    sid = submit(c)
    job = claim(c).json()
    assert "HIDDEN-EXPECTED" in str(job["tests"])  # only over the worker-authenticated channel
    assert "HIDDEN-EXPECTED" not in str(c.get(f"/api/v1/submissions/{sid}", headers=H()).json())
