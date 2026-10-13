import json
import uuid

from tests.conftest import H
from tests.fakes import CP1, CP2, CP3, EX, LID, Q1, Q2, Q3, SEG


def k():
    return str(uuid.uuid4())


def answer(c, cp, q, opt, token="learner1", key=None):
    return c.post(f"/api/v1/checkpoints/{cp}/attempts", headers=H(token, key or k()),
                  json={"question_id": q, "selected_option_id": opt})


def session(c, token="learner1"):
    return c.get(f"/api/v1/lectures/{LID}/session", headers=H(token)).json()


def patch(c, seg, version, token="learner1", pos=5):
    return c.patch(f"/api/v1/lectures/{LID}/session", headers=H(token),
                   json={"current_segment_id": seg, "playback_position_seconds": pos, "state_version": version})


def test_new_session_starts_at_first_segment_with_gate_at_first_checkpoint(env):
    c, *_ = env
    s = session(c)
    assert s["current_segment_id"] == SEG[1] and s["status"] == "in_progress" and s["state_version"] == 1
    assert s["max_reachable_order"] == 2 and s["completed_checkpoint_ids"] == []


def test_cannot_seek_past_required_checkpoint(env):
    c, *_ = env
    s = session(c)
    r = patch(c, SEG[3], s["state_version"])
    assert r.status_code == 400 and r.json()["error"]["code"] == "CHECKPOINT_REQUIRED"
    assert patch(c, SEG[2], s["state_version"]).status_code == 200  # the gate itself is reachable


def test_wrong_answer_still_completes_formative_checkpoint_and_unlocks(env):
    c, *_ = env
    r = answer(c, CP1, Q1, "a")
    body = r.json()
    assert r.status_code == 200 and body["is_correct"] is False and body["score"] == 0
    assert body["checkpoint_completed"] is True and body["explanation"] == "Wrong; see X"
    s = session(c)
    assert s["max_reachable_order"] == 4
    assert patch(c, SEG[3], s["state_version"]).status_code == 200


def test_response_never_leaks_answer_key(env):
    c, *_ = env
    for opt in ("a", "b"):
        assert "correct_option" not in json.dumps(answer(c, CP1, Q1, opt).json())
    assert "correct_option" not in json.dumps(c.get(f"/api/v1/lectures/{LID}", headers=H()).json())
    assert "correct_option" not in json.dumps(session(c))


def test_client_cannot_inject_correctness_or_score(env):
    c, *_ = env
    r = c.post(f"/api/v1/checkpoints/{CP1}/attempts", headers=H("learner1", k()),
               json={"question_id": Q1, "selected_option_id": "a", "is_correct": True, "score": 99})
    assert r.json()["is_correct"] is False and r.json()["score"] == 0


def test_invalid_inputs(env):
    c, *_ = env
    assert answer(c, CP1, Q1, "zzz").status_code == 422
    assert answer(c, CP1, Q2, "a").status_code == 422  # question from another checkpoint
    assert c.post(f"/api/v1/checkpoints/{CP1}/attempts", headers=H(),
                  json={"question_id": Q1, "selected_option_id": "a"}).status_code == 422  # no idempotency key
    assert answer(c, "00000000-0000-4000-8000-0000000000ff", Q1, "a").status_code == 404


def test_mcq_idempotency(env):
    c, repo, _ = env
    key = k()
    r1 = answer(c, CP1, Q1, "b", key=key).json()
    r2 = answer(c, CP1, Q1, "b", key=key).json()
    assert r1["attempt_id"] == r2["attempt_id"] and len(repo.attempts) == 1
    assert answer(c, CP1, Q1, "a", key=key).status_code == 409


def test_cannot_answer_later_checkpoint_before_earlier(env):
    c, *_ = env
    r = answer(c, CP2, Q2, "a")
    assert r.status_code == 400 and r.json()["error"]["code"] == "CHECKPOINT_REQUIRED"


def test_refresh_restores_result_and_explanation(env):
    c, *_ = env
    answer(c, CP1, Q1, "a")
    res = session(c)["checkpoint_results"][CP1]
    assert res["explanation"] == "Wrong; see X" and res["is_correct"] is False


def test_stale_state_version_conflict(env):
    c, *_ = env
    s = session(c)
    assert patch(c, SEG[1], s["state_version"]).status_code == 200
    assert patch(c, SEG[1], s["state_version"]).status_code == 409


def test_sessions_are_per_learner(env):
    c, *_ = env
    answer(c, CP1, Q1, "b")
    assert session(c, "learner2")["completed_checkpoint_ids"] == []


def test_patch_rejects_segment_from_elsewhere_and_bad_position(env):
    c, *_ = env
    s = session(c)
    assert patch(c, "00000000-0000-4000-8000-0000000000ff", s["state_version"]).status_code == 422
    assert patch(c, SEG[1], s["state_version"], pos=-1).status_code == 422


def test_completion_requires_all_gates(env):
    c, *_ = env
    r = c.post(f"/api/v1/lectures/{LID}/complete", headers=H(), json={"exit_check_completed": True})
    assert r.status_code == 400 and r.json()["error"]["code"] == "REQUIREMENTS_NOT_MET"
    assert len(r.json()["error"]["details"]) == 4  # cp1, cp2, exercise, exit check


def pass_everything(c):
    answer(c, CP1, Q1, "b")
    answer(c, CP2, Q2, "a")
    sub = c.post(f"/api/v1/exercises/{EX}/submissions", headers=H("learner1", k()), json={"source_code": "GOOD"})
    assert sub.status_code == 202
    return sub.json()["submission_id"]


def test_full_happy_path_and_exit_check_threshold(env):
    c, repo, _ = env
    pass_everything(c)
    assert answer(c, CP3, Q3, "a").json()["checkpoint_completed"] is False  # exit check needs 100%
    assert c.post(f"/api/v1/lectures/{LID}/complete", headers=H(), json={}).status_code == 400
    assert answer(c, CP3, Q3, "c").json()["checkpoint_completed"] is True
    r = c.post(f"/api/v1/lectures/{LID}/complete", headers=H(), json={})
    assert r.status_code == 200 and r.json()["status"] == "completed"
    again = c.post(f"/api/v1/lectures/{LID}/complete", headers=H(), json={})
    assert again.status_code == 200 and again.json()["completed_at"] == r.json()["completed_at"]
    assert len(repo.progress) == 1


def test_exercise_locked_until_checkpoints_done(env):
    c, *_ = env
    r = c.post(f"/api/v1/exercises/{EX}/submissions", headers=H("learner1", k()), json={"source_code": "GOOD"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "CHECKPOINT_REQUIRED"


def test_exercise_config_hides_tests(env):
    c, *_ = env
    body = json.dumps(c.get(f"/api/v1/exercises/{EX}", headers=H()).json())
    assert "HIDDEN-EXPECTED" not in body and "tests" not in body and "starter_code" in body


def test_fail_then_retry_keeps_both_attempts(env):
    c, repo, _ = env
    answer(c, CP1, Q1, "b")
    answer(c, CP2, Q2, "a")
    s1 = c.post(f"/api/v1/exercises/{EX}/submissions", headers=H("learner1", k()), json={"source_code": "bad"}).json()
    assert c.get(f"/api/v1/submissions/{s1['submission_id']}", headers=H()).json()["status"] == "failed"
    assert session(c)["completed_exercise_ids"] == []
    s2 = c.post(f"/api/v1/exercises/{EX}/submissions", headers=H("learner1", k()), json={"source_code": "GOOD"}).json()
    assert c.get(f"/api/v1/submissions/{s2['submission_id']}", headers=H()).json()["status"] == "passed"
    assert session(c)["completed_exercise_ids"] == [EX]
    listed = c.get(f"/api/v1/exercises/{EX}/submissions", headers=H()).json()["submissions"]
    assert [s["submission_number"] for s in listed] == [1, 2] and len(repo.submissions) == 2


def test_grader_outage_is_infrastructure_error_not_failure_and_not_counted(env):
    c, _, grader = env
    answer(c, CP1, Q1, "b")
    answer(c, CP2, Q2, "a")
    grader.down = True
    for _ in range(5):  # more than max_attempts=3
        r = c.post(f"/api/v1/exercises/{EX}/submissions", headers=H("learner1", k()), json={"source_code": "GOOD"})
        assert r.status_code == 202
        v = c.get(f"/api/v1/submissions/{r.json()['submission_id']}", headers=H()).json()
        assert v["status"] == "error" and v["infrastructure_error"] is True
    assert session(c)["completed_exercise_ids"] == []
    grader.down = False
    assert c.post(f"/api/v1/exercises/{EX}/submissions", headers=H("learner1", k()), json={"source_code": "GOOD"}).status_code == 202


def test_attempt_limit_enforced(env):
    c, *_ = env
    answer(c, CP1, Q1, "b")
    answer(c, CP2, Q2, "a")
    for _ in range(3):
        assert c.post(f"/api/v1/exercises/{EX}/submissions", headers=H("learner1", k()), json={"source_code": "bad"}).status_code == 202
    r = c.post(f"/api/v1/exercises/{EX}/submissions", headers=H("learner1", k()), json={"source_code": "bad"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "ATTEMPTS_EXHAUSTED"


def test_submission_idempotency_and_validation(env):
    c, repo, grader = env
    answer(c, CP1, Q1, "b")
    answer(c, CP2, Q2, "a")
    key = k()
    a = c.post(f"/api/v1/exercises/{EX}/submissions", headers=H("learner1", key), json={"source_code": "GOOD"}).json()
    b = c.post(f"/api/v1/exercises/{EX}/submissions", headers=H("learner1", key), json={"source_code": "GOOD"}).json()
    assert a["submission_id"] == b["submission_id"] and len(repo.submissions) == 1 and len(grader.calls) == 1
    assert c.post(f"/api/v1/exercises/{EX}/submissions", headers=H("learner1", key), json={"source_code": "other"}).status_code == 409
    assert c.post(f"/api/v1/exercises/{EX}/submissions", headers=H("learner1", k()), json={"source_code": "  "}).status_code == 422
    assert c.post(f"/api/v1/exercises/{EX}/submissions", headers=H("learner1", k()), json={"source_code": "x" * 50001}).status_code == 422


def test_grader_receives_tests_but_responses_never_expose_them(env):
    c, _, grader = env
    sid = pass_everything(c)
    assert grader.calls[0][1][0]["definition"] == {"secret": "HIDDEN-EXPECTED"}
    assert "HIDDEN-EXPECTED" not in json.dumps(c.get(f"/api/v1/submissions/{sid}", headers=H()).json())


def test_cross_user_submission_access_denied(env):
    c, *_ = env
    sid = pass_everything(c)
    assert c.get(f"/api/v1/submissions/{sid}", headers=H("learner2")).status_code == 404
    assert c.get(f"/api/v1/submissions/{sid}", headers=H("teacher")).status_code == 200
    assert c.get(f"/api/v1/exercises/{EX}/submissions", headers=H("learner2")).json()["submissions"] == []
    assert c.get(f"/api/v1/checkpoints/{CP1}/attempts", headers=H("learner2")).json()["attempts"] == []


def test_stuck_submission_becomes_infrastructure_error(env):
    c, repo, _ = env
    sid = pass_everything(c)
    sub = next(s for s in repo.submissions if s["id"] == sid)
    sub.update(status="running", created_at="2020-01-01T00:00:00+00:00")
    v = c.get(f"/api/v1/submissions/{sid}", headers=H()).json()
    assert v["status"] == "error" and v["infrastructure_error"] is True


def test_teacher_endpoints_and_role_enforcement(env):
    c, repo, _ = env
    l1 = "11111111-1111-4111-8111-111111111111"
    repo.profiles[l1] = {"id": l1, "display_name": "Asha", "role": "learner"}
    pass_everything(c)
    assert c.get("/api/v1/teacher/learners", headers=H("learner1")).status_code == 403
    assert c.get(f"/api/v1/teacher/learners/{l1}/results", headers=H("learner2")).status_code == 403
    assert c.get("/api/v1/teacher/learners").status_code == 401
    r = c.get(f"/api/v1/teacher/learners/{l1}/results", headers=H("teacher"))
    body = r.json()
    assert r.status_code == 200 and body["learner"]["display_name"] == "Asha"
    assert len(body["checkpoint_attempts"]) == 2 and body["submissions"][0]["status"] == "passed"
    assert "source_code" not in json.dumps(body)
    assert c.get("/api/v1/teacher/learners/not-a-uuid/results", headers=H("teacher")).status_code == 404


def test_unauthenticated_everything(env):
    c, *_ = env
    for method, path in [("get", f"/api/v1/lectures/{LID}/session"), ("patch", f"/api/v1/lectures/{LID}/session"),
                         ("post", f"/api/v1/checkpoints/{CP1}/attempts"), ("post", f"/api/v1/exercises/{EX}/submissions"),
                         ("post", f"/api/v1/lectures/{LID}/complete"), ("get", f"/api/v1/exercises/{EX}")]:
        assert getattr(c, method)(path).status_code == 401, path
