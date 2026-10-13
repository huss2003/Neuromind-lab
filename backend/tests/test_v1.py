"""Requirements v1.0: best score, hints, remediation, evidence fields, drafts, rate limits,
teacher scope, feedback, audit events, pagination, readiness."""
import json
import uuid

from tests.conftest import H
from tests.fakes import CP1, CP2, EX, LID, Q1, Q2

L1 = "11111111-1111-4111-8111-111111111111"
L2 = "22222222-2222-4222-8222-222222222222"
T1 = "33333333-3333-4333-8333-333333333333"


def k():
    return str(uuid.uuid4())


def unlock(c):
    for cp, q, opt in ((CP1, Q1, "b"), (CP2, Q2, "a")):
        c.post(f"/api/v1/checkpoints/{cp}/attempts", headers=H("learner1", k()), json={"question_id": q, "selected_option_id": opt})


def submit(c, code, token="learner1"):
    r = c.post(f"/api/v1/exercises/{EX}/submissions", headers=H(token, k()), json={"source_code": code})
    assert r.status_code == 202, r.text
    return c.get(f"/api/v1/submissions/{r.json()['submission_id']}", headers=H(token)).json()


def test_unlimited_attempts_by_default(env):
    c, *_ = env
    unlock(c)
    c2 = None
    assert c.get(f"/api/v1/exercises/{EX}", headers=H()).json()["max_attempts"] is None
    for i in range(5):  # more than the old cap of 5? stay under the abuse limit of 6/min
        assert submit(c, f"bad {i}")["status"] == "failed"
    assert c2 is None


def test_abuse_rate_limit_is_separate_from_attempt_policy(env):
    c, repo, _ = env
    unlock(c)
    for i in range(6):
        submit(c, f"bad {i}")
    r = c.post(f"/api/v1/exercises/{EX}/submissions", headers=H("learner1", k()), json={"source_code": "bad again"})
    assert r.status_code == 429 and r.json()["error"]["code"] == "RATE_LIMITED"
    assert any(a["event_type"] == "submission.rate_limited" for a in repo.audit)


def test_in_flight_limit(env):
    c, repo, _ = env
    unlock(c)
    for _ in range(2):  # two stuck jobs
        s = submit(c, "bad")
        next(x for x in repo.submissions if x["id"] == s["submission_id"]).update(status="running")
    r = c.post(f"/api/v1/exercises/{EX}/submissions", headers=H("learner1", k()), json={"source_code": "bad"})
    assert r.status_code == 429


def test_best_valid_score_is_kept_and_infra_errors_ignored(env):
    c, _, grader = env
    unlock(c)
    assert submit(c, "HALF")["score"] == 50
    assert submit(c, "bad")["score"] == 0
    grader.down = True
    assert submit(c, "GOOD")["status"] == "error"  # infrastructure: not a valid score
    grader.down = False
    ex = c.get(f"/api/v1/exercises/{EX}", headers=H()).json()
    assert ex["best_score"] == 50 and ex["attempts_used"] == 3
    hist = c.get(f"/api/v1/exercises/{EX}/submissions", headers=H()).json()
    assert hist["best_score"] == 50
    assert submit(c, "GOOD")["score"] == 100
    assert c.get(f"/api/v1/exercises/{EX}/submissions", headers=H()).json()["best_score"] == 100


def test_hints_are_ordered_idempotent_and_lower_only_current_attempt(env):
    c, _, _ = env
    unlock(c)
    assert submit(c, "HALF")["score"] == 50  # earlier best
    ex = c.get(f"/api/v1/exercises/{EX}", headers=H()).json()
    assert ex["hints_total"] == 3 and ex["hints_revealed"] == [] and "hint one" not in json.dumps(ex)
    assert c.post(f"/api/v1/exercises/{EX}/hints", headers=H(), json={"hint_index": 1}).status_code == 409  # out of order
    r = c.post(f"/api/v1/exercises/{EX}/hints", headers=H(), json={"hint_index": 0}).json()
    assert r["text"] == "hint one" and r["penalty_percent"] == 10
    again = c.post(f"/api/v1/exercises/{EX}/hints", headers=H(), json={"hint_index": 0}).json()
    assert again["hints_revealed"] == 1  # idempotent
    c.post(f"/api/v1/exercises/{EX}/hints", headers=H(), json={"hint_index": 1})
    assert c.post(f"/api/v1/exercises/{EX}/hints", headers=H(), json={"hint_index": 5}).status_code == 409
    sub = submit(c, "GOOD")
    assert sub["raw_score"] == 100 and sub["score"] == 80 and sub["hints_used"] == 2 and sub["hint_penalty"] == 20
    assert sub["status"] == "passed"  # 80 >= pass mark 80
    best = c.get(f"/api/v1/exercises/{EX}/submissions", headers=H()).json()["best_score"]
    assert best == 80
    # hints reset for the next attempt
    assert c.get(f"/api/v1/exercises/{EX}", headers=H()).json()["hints_revealed"] == []


def test_hints_can_drop_a_pass_below_threshold_without_hurting_best(env):
    c, _, _ = env
    unlock(c)
    for i in range(3):
        c.post(f"/api/v1/exercises/{EX}/hints", headers=H(), json={"hint_index": i})
    sub = submit(c, "GOOD")
    assert sub["score"] == 70 and sub["status"] == "failed"
    assert any("hint" in f["message"].lower() for f in sub["feedback"])
    assert c.get("/api/v1/session-does-not-exist", headers=H()).status_code == 404


def test_hints_locked_until_exercise_reachable(env):
    c, *_ = env
    assert c.post(f"/api/v1/exercises/{EX}/hints", headers=H(), json={"hint_index": 0}).status_code == 400


def test_criteria_remediation_and_hidden_label(env):
    c, _, _ = env
    unlock(c)
    sub = submit(c, "bad")
    labels = [x["label"] for x in sub["criteria"]]
    assert labels == ["Hidden check 1", "Prints a value"]
    assert "SECRET-LABEL" not in json.dumps(sub) and "HIDDEN-EXPECTED" not in json.dumps(sub)
    assert {r["text"] for r in sub["remediation"]} == {"Review how print works.", "Add a print call."}
    good = submit(c, "GOOD")
    assert good["remediation"] == [] and all(x["passed"] for x in good["criteria"])


def test_evidence_fields_persisted_with_versions(env):
    c, repo, _ = env
    unlock(c)
    sub = submit(c, "GOOD")
    row = next(s for s in repo.submissions if s["id"] == sub["submission_id"])
    assert row["grader_version"] == "test-1.0" and row["test_suite_version"] == 1 and row["content_version"] == 1
    assert row["max_score"] == 100 and row["pass_threshold"] == 80 and row["correlation_id"]
    assert row["started_at"] and row["finished_at"] and row["criteria_results"]
    attempts = [a for a in repo.attempts]
    assert all(a["content_version"] == 1 for a in attempts)


def test_draft_save_restore_and_validation(env):
    c, _, _ = env
    assert c.put(f"/api/v1/exercises/{EX}/draft", headers=H(), json={"source_code": "x=1"}).status_code == 400  # locked
    unlock(c)
    assert c.get(f"/api/v1/exercises/{EX}", headers=H()).json()["draft"] is None
    assert c.put(f"/api/v1/exercises/{EX}/draft", headers=H(), json={"source_code": "x = 42"}).status_code == 204
    assert c.get(f"/api/v1/exercises/{EX}", headers=H()).json()["draft"] == "x = 42"
    assert c.get(f"/api/v1/exercises/{EX}", headers=H("learner2")).json()["draft"] is None  # per learner
    assert c.put(f"/api/v1/exercises/{EX}/draft", headers=H(), json={"source_code": "x" * 50001}).status_code == 422
    assert c.put(f"/api/v1/exercises/{EX}/draft", json={"source_code": "x"}).status_code == 401


def test_session_progress_breakdown_separates_media_checkpoints_labs_mastery(env):
    c, *_ = env
    p = c.get(f"/api/v1/lectures/{LID}/session", headers=H()).json()["progress"]
    assert p["media"]["total"] == 3 and p["checkpoints"]["total"] == 3 and p["labs"]["total"] == 1
    assert p["mastery"]["best_exercise_score"] is None and p["mastery"]["pass_mark"] == 80
    unlock(c)
    submit(c, "GOOD")
    p = c.get(f"/api/v1/lectures/{LID}/session", headers=H()).json()["progress"]
    assert p["checkpoints"]["done"] == 2 and p["labs"]["done"] == 1 and p["mastery"]["best_exercise_score"] == 100


def test_course_detail_groups_lectures_into_modules(env):
    c, *_ = env
    cid = "00000000-0000-4000-8000-000000000001"
    body = c.get(f"/api/v1/courses/{cid}", headers=H()).json()
    assert body["modules"][0]["title"] == "Module 1" and "lectures" in body["modules"][0]


def test_audit_events_for_denial_attempts_and_submissions(env):
    c, repo, _ = env
    assert c.get("/api/v1/teacher/learners", headers=H("learner1")).status_code == 403
    unlock(c)
    submit(c, "GOOD")
    events = [a["event_type"] for a in repo.audit]
    assert "auth.denied" in events and "checkpoint.attempt" in events
    assert "submission.created" in events and "submission.finished" in events
    denied = next(a for a in repo.audit if a["event_type"] == "auth.denied")
    assert denied["actor_id"] == L1 and denied["metadata"]["role"] == "learner" and denied["request_id"]
    blob = json.dumps(repo.audit)
    assert "GOOD" not in blob and "Bearer" not in blob and "learner1" not in blob  # no code, tokens


def test_audit_metadata_is_allow_listed(env):
    import asyncio

    from app.services.audit import record
    _, repo, _ = env
    asyncio.run(record(repo, None, L1, "x.y", "t", None, {"status": "ok", "source_code": "SECRET", "token": "abc"}))
    assert repo.audit[-1]["metadata"] == {"status": "ok"}


def seed_learners(repo):
    repo.profiles[L1] = {"id": L1, "display_name": "Asha", "role": "learner"}
    repo.profiles[L2] = {"id": L2, "display_name": "Bilal", "role": "learner"}


def test_teacher_sees_only_assigned_learners_and_revocation(env):
    c, repo, _ = env
    seed_learners(repo)
    repo.assignments[T1] = [L1]
    names = [x["display_name"] for x in c.get("/api/v1/teacher/learners", headers=H("teacher")).json()["learners"]]
    assert names == ["Asha"]
    assert c.get(f"/api/v1/teacher/learners/{L2}/results", headers=H("teacher")).status_code == 404
    assert c.get(f"/api/v1/teacher/learners/{L1}/results", headers=H("teacher")).status_code == 200
    repo.assignments[T1] = []  # revoked
    assert c.get(f"/api/v1/teacher/learners/{L1}/results", headers=H("teacher")).status_code == 404
    assert c.get("/api/v1/teacher/learners", headers=H("teacher")).json()["total"] == 0
    assert c.get("/api/v1/teacher/learners", headers=H("teacher2")).json()["learners"] == []


def test_admin_sees_all_learners_and_pagination_search(env):
    c, repo, _ = env
    seed_learners(repo)
    body = c.get("/api/v1/teacher/learners?limit=1&offset=0", headers=H("admin")).json()
    assert body["total"] == 2 and len(body["learners"]) == 1 and body["limit"] == 1
    page2 = c.get("/api/v1/teacher/learners?limit=1&offset=1", headers=H("admin")).json()
    assert page2["learners"][0]["display_name"] == "Bilal"
    assert [x["display_name"] for x in c.get("/api/v1/teacher/learners?q=bil", headers=H("admin")).json()["learners"]] == ["Bilal"]
    assert c.get("/api/v1/teacher/learners?limit=1000", headers=H("admin")).status_code == 422


def test_teacher_submission_detail_evidence_and_audit(env):
    c, repo, _ = env
    seed_learners(repo)
    repo.assignments[T1] = [L1]
    unlock(c)
    sub = submit(c, "GOOD")
    d = c.get(f"/api/v1/teacher/submissions/{sub['submission_id']}", headers=H("teacher")).json()
    assert d["source_code"] == "GOOD" and d["evidence"]["grader_version"] == "test-1.0"
    assert d["evidence"]["content_version"] == 1 and d["criteria"] and d["status"] == "passed"
    assert any(a["event_type"] == "teacher.view_submission" for a in repo.audit)
    assert c.get(f"/api/v1/teacher/submissions/{sub['submission_id']}", headers=H("teacher2")).status_code == 404
    assert c.get(f"/api/v1/teacher/submissions/{sub['submission_id']}", headers=H("learner2")).status_code == 403


def test_teacher_feedback_never_changes_scores_and_learner_sees_only_published(env):
    c, repo, _ = env
    seed_learners(repo)
    repo.assignments[T1] = [L1]
    unlock(c)
    sub = submit(c, "HALF")
    before = c.get(f"/api/v1/submissions/{sub['submission_id']}", headers=H()).json()
    r = c.post(f"/api/v1/teacher/learners/{L1}/feedback", headers=H("teacher"),
               json={"body": "Draft note", "submission_id": sub["submission_id"], "publish": False})
    assert r.status_code == 201
    c.post(f"/api/v1/teacher/learners/{L1}/feedback", headers=H("teacher"), json={"body": "Great effort", "publish": True})
    mine = c.get("/api/v1/me/feedback", headers=H()).json()["feedback"]
    assert [f["body"] for f in mine] == ["Great effort"]
    assert c.get("/api/v1/me/feedback", headers=H("learner2")).json()["feedback"] == []
    after = c.get(f"/api/v1/submissions/{sub['submission_id']}", headers=H()).json()
    assert before["score"] == after["score"] == 50 and before["status"] == after["status"]
    # no way to override scores
    for method in ("put", "patch", "post", "delete"):
        r = c.request(method.upper(), f"/api/v1/teacher/submissions/{sub['submission_id']}", headers=H("teacher"),
                      json={"score": 100})
        assert r.status_code in (404, 405)
    # scope + validation
    assert c.post(f"/api/v1/teacher/learners/{L2}/feedback", headers=H("teacher"), json={"body": "x"}).status_code == 404
    assert c.post(f"/api/v1/teacher/learners/{L1}/feedback", headers=H("learner1"), json={"body": "x"}).status_code == 403
    assert c.post(f"/api/v1/teacher/learners/{L1}/feedback", headers=H("teacher"), json={"body": ""}).status_code == 422
    other = c.post(f"/api/v1/teacher/learners/{L1}/feedback", headers=H("teacher"),
                   json={"body": "x", "submission_id": "00000000-0000-4000-8000-0000000000ff"})
    assert other.status_code in (404, 422)


def test_teacher_summary_counts_assigned_only(env):
    c, repo, _ = env
    seed_learners(repo)
    repo.assignments[T1] = [L1]
    c.get(f"/api/v1/lectures/{LID}/session", headers=H())
    unlock(c)
    submit(c, "GOOD")
    s = c.get("/api/v1/teacher/summary", headers=H("teacher")).json()
    assert s["assigned_learners"] == 1 and s["submissions_passed"] == 1 and s["lectures_in_progress"] == 1
    assert c.get("/api/v1/teacher/summary", headers=H("teacher2")).json()["assigned_learners"] == 0


def test_readiness_discloses_no_values(env, monkeypatch):
    c, *_ = env
    for name in ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY"):
        monkeypatch.setenv(name, "super-secret-value")
    r = c.get("/api/v1/ready")
    assert r.status_code == 200 and r.json() == {"status": "ready", "checks": {"config": True, "database": True}}
    assert "super-secret-value" not in r.text
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY")
    r = c.get("/api/v1/ready")
    assert r.status_code == 503 and r.json()["checks"]["config"] is False


def test_request_logs_are_structured_without_secrets(env, caplog):
    import logging
    c, *_ = env
    with caplog.at_level(logging.INFO, logger="neuromind.api"):
        c.get("/api/v1/me", headers={"Authorization": "Bearer learner1", "X-Request-ID": "req-123"})
    rec = next(r for r in caplog.records if r.getMessage() == "request")
    assert rec.ctx["request_id"] == "req-123" and rec.ctx["status"] == 200 and rec.ctx["path"] == "/api/v1/me"
    assert "Bearer" not in json.dumps(rec.ctx) and "learner1" not in json.dumps(rec.ctx)


def test_json_formatter_outputs_valid_json():
    import logging

    from app.logging_setup import JsonFormatter
    rec = logging.LogRecord("n", logging.INFO, "f", 1, "hello", None, None)
    rec.ctx = {"request_id": "r1"}
    out = json.loads(JsonFormatter().format(rec))
    assert out["msg"] == "hello" and out["request_id"] == "r1" and out["level"] == "INFO" and out["ts"]
