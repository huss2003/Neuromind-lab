"""Complete Flow & Working v1.0: enrolment, locking, orientation data, text sections, statuses, remediation,
dashboard, teacher analytics, admin operations, grader result validation."""
import json
import uuid

import pytest

from app.grader_client import InvalidGraderResult, validate_payload
from app.services.manifest import ManifestError, build_segment
from tests.conftest import H
from tests.fakes import CID, CP1, EX, LID, Q1, Q2, SEG

L1 = "11111111-1111-4111-8111-111111111111"
L2 = "22222222-2222-4222-8222-222222222222"
T1 = "33333333-3333-4333-8333-333333333333"
ADMIN = "55555555-5555-4555-8555-555555555555"
OTHER = "00000000-0000-4000-8000-0000000000aa"


def k():
    return str(uuid.uuid4())


def unlock(c):
    for cp, q, opt in ((CP1, Q1, "b"), ("00000000-0000-4000-8000-0000000000c2", Q2, "a")):
        c.post(f"/api/v1/checkpoints/{cp}/attempts", headers=H("learner1", k()), json={"question_id": q, "selected_option_id": opt})


def submit(c, code, token="learner1", **extra):
    r = c.post(f"/api/v1/exercises/{EX}/submissions", headers=H(token, k()), json={"source_code": code, **extra})
    return r


def result(c, r, token="learner1"):
    assert r.status_code == 202, r.text
    return c.get(f"/api/v1/submissions/{r.json()['submission_id']}", headers=H(token)).json()


# ---------- enrolment and locking ----------
def test_unenrolled_learner_sees_nothing(env):
    c, repo, _ = env
    repo.enrollments.pop(L2)
    assert c.get("/api/v1/courses", headers=H("learner2")).json()["courses"] == []
    assert c.get(f"/api/v1/courses/{CID}", headers=H("learner2")).status_code == 404
    assert c.get(f"/api/v1/lectures/{LID}", headers=H("learner2")).status_code == 404
    assert c.get(f"/api/v1/lectures/{LID}/session", headers=H("learner2")).status_code == 404
    d = c.get("/api/v1/me/dashboard", headers=H("learner2")).json()
    assert d["enrolled"] is False and d["course"] is None and d["remediation_queue"] == []


def test_teachers_and_admins_see_all_published_courses(env):
    c, *_ = env
    assert len(c.get("/api/v1/courses", headers=H("teacher")).json()["courses"]) == 1
    assert len(c.get("/api/v1/courses", headers=H("admin")).json()["courses"]) == 1


def test_prerequisite_locks_lecture_until_completed(env):
    c, repo, _ = env
    repo.d["lecture"]["prerequisites"] = [OTHER]
    r = c.get(f"/api/v1/lectures/{LID}", headers=H())
    assert r.status_code == 400 and r.json()["error"]["code"] == "LECTURE_LOCKED"
    assert c.get(f"/api/v1/lectures/{LID}/session", headers=H()).json()["error"]["code"] == "LECTURE_LOCKED"
    course = c.get(f"/api/v1/courses/{CID}", headers=H()).json()
    assert course["lectures"][0]["state"] == "locked"
    repo.sessions["s"] = {"id": "s", "learner_id": L1, "lecture_id": OTHER, "status": "completed", "current_segment_id": None,
                          "playback_position_seconds": 0, "state_version": 1, "last_seen_at": "x", "completed_at": "x"}
    assert c.get(f"/api/v1/lectures/{LID}", headers=H()).status_code == 200
    assert c.get(f"/api/v1/courses/{CID}", headers=H()).json()["lectures"][0]["state"] == "available"


def test_course_map_states_progress_through_the_lifecycle(env):
    c, *_ = env
    state = lambda: c.get(f"/api/v1/courses/{CID}", headers=H()).json()["lectures"][0]["state"]  # noqa: E731
    assert state() == "available"
    c.get(f"/api/v1/lectures/{LID}/session", headers=H())
    assert state() == "in_progress"
    unlock(c)
    assert result(c, submit(c, "bad"))["status"] == "failed"
    assert state() == "needs_attention"
    assert result(c, submit(c, "GOOD"))["status"] == "passed"
    assert state() == "in_progress"


# ---------- orientation and sections ----------
def test_manifest_includes_orientation(env):
    c, repo, _ = env
    repo.d["lecture"]["prerequisites"] = []
    m = c.get(f"/api/v1/lectures/{LID}", headers=H()).json()
    assert m["estimated_minutes"] == 60 and m["prerequisites"] == []
    assert any("3 knowledge checks" in x for x in m["completion_criteria"])
    assert any("at least 80%" in x for x in m["completion_criteria"])
    assert "as often as you like" in m["attempt_policy"] and "correct_option" not in json.dumps(m)


def test_text_sections_carry_a_body_and_media_sections_a_url():
    seg = {"id": "s", "segment_order": 1, "segment_type": "intro", "title": "Intro", "is_required": True,
           "settings": {"body": "Welcome"}, "media_url": None}
    out = build_segment(seg, None)
    assert out.body == "Welcome" and out.media is None
    ex = {**seg, "segment_type": "example", "media_url": "http://x/v.mp4", "settings": {}}
    assert build_segment(ex, None).media.url == "http://x/v.mp4"
    with pytest.raises(ManifestError):
        build_segment({**seg, "settings": {}}, None)  # empty text section is a content error


def test_text_sections_are_never_gates(env):
    c, repo, _ = env
    repo.d["segments"][0] = {**repo.d["segments"][0], "segment_type": "intro", "media_url": None, "settings": {"body": "Hi"}}
    m = c.get(f"/api/v1/lectures/{LID}", headers=H()).json()
    assert m["segments"][0]["type"] == "intro" and m["segments"][0]["body"] == "Hi"
    s = c.get(f"/api/v1/lectures/{LID}/session", headers=H()).json()
    assert s["max_reachable_order"] == 2


# ---------- lecture state vocabulary ----------
def test_lecture_state_vocabulary(env):
    c, _, _ = env
    sess = lambda: c.get(f"/api/v1/lectures/{LID}/session", headers=H()).json()["lecture_state"]  # noqa: E731
    assert sess() == "NOT_STARTED"
    unlock(c)
    assert sess() == "IN_PROGRESS"
    assert result(c, submit(c, "bad"))["status"] == "failed"
    assert sess() == "REMEDIATION_REQUIRED"
    assert result(c, submit(c, "GOOD"))["status"] == "passed"
    assert sess() == "IN_PROGRESS"
    c.post("/api/v1/checkpoints/00000000-0000-4000-8000-0000000000c3/attempts", headers=H("learner1", k()),
           json={"question_id": "00000000-0000-4000-8000-0000000000a3", "selected_option_id": "c"})
    c.post(f"/api/v1/lectures/{LID}/complete", headers=H(), json={})
    assert sess() == "COMPLETED"


def test_grading_pending_state_and_lecture_opened_audit(env):
    c, repo, _ = env
    unlock(c)
    s = submit(c, "GOOD").json()
    next(x for x in repo.submissions if x["id"] == s["submission_id"]).update(status="running")
    assert c.get(f"/api/v1/lectures/{LID}/session", headers=H()).json()["lecture_state"] == "GRADING_PENDING"
    assert [a["event_type"] for a in repo.audit].count("lecture.opened") == 1
    c.get(f"/api/v1/lectures/{LID}/session", headers=H())
    assert [a["event_type"] for a in repo.audit].count("lecture.opened") == 1


# ---------- exercise panel, statuses, remediation ----------
def test_exercise_panel_fields_and_hint_policy(env):
    c, repo, _ = env
    repo.d["exercise"].update(objective="Print a value", constraints="Use print once", visible_examples=[{"code": "x", "expected_output": "y"}],
                              success_criteria=["Prints something"])
    unlock(c)
    ex = c.get(f"/api/v1/exercises/{EX}", headers=H()).json()
    assert ex["objective"] == "Print a value" and ex["constraints"] == "Use print once"
    assert ex["visible_examples"][0]["expected_output"] == "y" and ex["success_criteria"] == ["Prints something"]
    assert "never lowers a score you already earned" in ex["hints_policy"] and ex["content_version"] == 1
    assert ex["runtime"].startswith("Python")
    blob = json.dumps(ex)
    assert "HIDDEN-EXPECTED" not in blob and "SECRET-LABEL" not in blob


def test_runtime_error_status_is_an_evaluated_failure_with_bounded_message(env):
    c, _, _ = env
    unlock(c)
    sub = result(c, submit(c, "CRASH"))
    assert sub["status"] == "runtime_error" and sub["score"] == 0 and sub["infrastructure_error"] is False
    assert any("line 1" in f["message"] for f in sub["feedback"])
    best = c.get(f"/api/v1/exercises/{EX}/submissions", headers=H()).json()["best_score"]
    assert best == 0


def test_time_limit_is_not_a_valid_score_and_not_infrastructure(env):
    c, _, _ = env
    unlock(c)
    assert result(c, submit(c, "HALF"))["score"] == 50
    t = result(c, submit(c, "TIMEOUT"))
    assert t["status"] == "timeout" and t["infrastructure_error"] is False
    assert c.get(f"/api/v1/exercises/{EX}/submissions", headers=H()).json()["best_score"] == 50  # unchanged


def test_remediation_maps_to_objective_and_replayable_section(env):
    c, _, _ = env
    unlock(c)
    sub = result(c, submit(c, "bad"))
    steps = {r["objective"]: r for r in sub["remediation"]}
    assert steps["Print output"]["review_segment_id"] == SEG[5] and steps["Print output"]["review_title"] == "S5"
    assert steps["Variables"]["review_title"] == "S3"
    assert result(c, submit(c, "GOOD"))["remediation"] == []


def test_language_and_content_version_are_validated(env):
    c, _, _ = env
    unlock(c)
    assert submit(c, "GOOD", language="javascript").status_code == 422
    assert submit(c, "GOOD", language="Python", content_version=1).status_code == 202
    r = submit(c, "GOOD", content_version=7)
    assert r.status_code == 409 and r.json()["error"]["code"] == "CONTENT_CHANGED"


def test_snapshot_hash_is_stored_and_never_trusted_from_client(env):
    import hashlib
    c, repo, _ = env
    unlock(c)
    r = submit(c, "GOOD", snapshot_sha256="forged")
    row = next(x for x in repo.submissions if x["id"] == r.json()["submission_id"])
    assert row["snapshot_sha256"] == hashlib.sha256(b"GOOD").hexdigest()


def test_draft_tied_to_content_version_goes_stale_when_content_changes(env):
    c, repo, _ = env
    unlock(c)
    c.put(f"/api/v1/exercises/{EX}/draft", headers=H(), json={"source_code": "mine"})
    assert c.get(f"/api/v1/exercises/{EX}", headers=H()).json()["draft"] == "mine"
    repo.d["lecture"]["content_version"] = 2
    ex = c.get(f"/api/v1/exercises/{EX}", headers=H()).json()
    assert ex["draft"] is None and ex["draft_stale"] is True


# ---------- questions ----------
def test_option_shuffle_is_stable_per_learner_and_does_not_change_correctness(env):
    c, repo, _ = env
    repo.d["questions"][Q1]["shuffle_options"] = True
    def opts(token):
        m = c.get(f"/api/v1/lectures/{LID}", headers=H(token)).json()
        return [o["id"] for o in m["segments"][1]["checkpoint"]["question"]["options"]]
    a1, a2, b = opts("learner1"), opts("learner1"), opts("learner2")
    assert a1 == a2 and sorted(a1) == ["a", "b", "c"] and sorted(b) == ["a", "b", "c"]
    orders = {tuple(opts(t)) for t in ("learner1", "learner2")}
    assert len(orders) >= 1
    r = c.post(f"/api/v1/checkpoints/{CP1}/attempts", headers=H("learner1", k()), json={"question_id": Q1, "selected_option_id": "b"})
    assert r.json()["is_correct"] is True  # correct by id regardless of position


def test_reveal_policy_after_correct_withholds_explanation_until_correct(env):
    c, repo, _ = env
    repo.d["questions"][Q1]["reveal_policy"] = "after_correct"
    wrong = c.post(f"/api/v1/checkpoints/{CP1}/attempts", headers=H("learner1", k()), json={"question_id": Q1, "selected_option_id": "a"}).json()
    assert "Wrong; see X" not in json.dumps(wrong) and "try again" in wrong["explanation"]
    right = c.post(f"/api/v1/checkpoints/{CP1}/attempts", headers=H("learner1", k()), json={"question_id": Q1, "selected_option_id": "b"}).json()
    assert right["explanation"] == "Right because X"
    sess = c.get(f"/api/v1/lectures/{LID}/session", headers=H()).json()
    assert sess["checkpoint_results"][CP1]["explanation"] == "Right because X"


def test_question_version_mismatch_is_a_conflict(env):
    c, repo, _ = env
    repo.d["questions"][Q1]["question_version"] = 3
    base = {"question_id": Q1, "selected_option_id": "b"}
    r = c.post(f"/api/v1/checkpoints/{CP1}/attempts", headers=H("learner1", k()), json={**base, "question_version": 2})
    assert r.status_code == 409 and r.json()["error"]["code"] == "CONTENT_CHANGED"
    assert c.post(f"/api/v1/checkpoints/{CP1}/attempts", headers=H("learner1", k()), json={**base, "question_version": 3}).status_code == 200
    assert repo.attempts[-1]["question_version"] == 3


# ---------- dashboard ----------
def test_dashboard_is_scoped_and_lists_attempts_and_remediation(env):
    c, _, _ = env
    unlock(c)
    submit(c, "HALF")
    d = c.get("/api/v1/me/dashboard", headers=H()).json()
    assert d["enrolled"] is True and d["course"]["total_lectures"] == 1 and d["continue"]["lecture_number"] == 9
    assert d["recent_attempts"][0]["status"] == "failed" and d["recent_attempts"][0]["best_score"] == 50
    q = d["remediation_queue"][0]
    assert q["exercise"] == "Print" and "Print output" in q["objectives"] and q["steps"]
    other = c.get("/api/v1/me/dashboard", headers=H("learner2")).json()
    assert other["recent_attempts"] == [] and other["remediation_queue"] == []
    submit(c, "GOOD")
    assert c.get("/api/v1/me/dashboard", headers=H()).json()["remediation_queue"] == []


# ---------- teacher ----------
def seed_learners(repo):
    repo.profiles[L1] = {"id": L1, "display_name": "Asha", "role": "learner"}
    repo.profiles[L2] = {"id": L2, "display_name": "Bilal", "role": "learner"}


def test_teacher_needs_support_filter_and_summary_fields(env):
    c, repo, _ = env
    seed_learners(repo)
    repo.assignments[T1] = [L1, L2]
    unlock(c)
    for i in range(3):
        submit(c, f"bad {i}")
    body = c.get("/api/v1/teacher/learners", headers=H("teacher")).json()
    asha = next(x for x in body["learners"] if x["display_name"] == "Asha")
    assert asha["needs_support"] is True and asha["lectures_in_progress"] == 0 and "last_active" in asha
    flagged = c.get("/api/v1/teacher/learners?needs_support=true", headers=H("teacher")).json()
    assert [x["display_name"] for x in flagged["learners"]] == ["Asha"] and flagged["total"] == 1
    assert c.get("/api/v1/teacher/learners?progress=bogus", headers=H("teacher")).status_code == 422
    assert c.get("/api/v1/teacher/learners?needs_support=true", headers=H("learner1")).status_code == 403


def test_teacher_exercise_analytics(env):
    c, repo, grader = env
    seed_learners(repo)
    repo.assignments[T1] = [L1]
    unlock(c)
    submit(c, "bad")
    submit(c, "HALF")
    grader.down = True
    submit(c, "GOOD")
    grader.down = False
    submit(c, "GOOD")
    a = c.get("/api/v1/teacher/analytics/exercises", headers=H("teacher")).json()["exercises"][0]
    assert a["attempts"] == 4 and a["learners"] == 1 and a["completion_rate"] == 100.0 and a["system_errors"] == 1
    assert a["score_distribution"] == {"below_50": 1, "50_to_79": 1, "80_and_above": 1}
    assert a["common_failures"][0]["count"] >= 1
    assert c.get("/api/v1/teacher/analytics/exercises", headers=H("teacher2")).json()["exercises"] == []
    assert "HIDDEN-EXPECTED" not in json.dumps(a)


def test_teacher_content_status(env):
    c, *_ = env
    lec = c.get("/api/v1/teacher/content-status", headers=H("teacher")).json()["lectures"][0]
    assert lec["status"] == "published" and lec["version"] == 1
    assert c.get("/api/v1/teacher/content-status", headers=H("learner1")).status_code == 403


# ---------- admin ----------
def test_admin_role_change_is_audited_and_guarded(env):
    c, repo, _ = env
    seed_learners(repo)
    repo.profiles[ADMIN] = {"id": ADMIN, "display_name": "Root", "role": "admin"}
    assert c.patch(f"/api/v1/admin/users/{L1}/role", headers=H("teacher"), json={"role": "admin"}).status_code == 403
    assert c.patch(f"/api/v1/admin/users/{L1}/role", headers=H("learner1"), json={"role": "admin"}).status_code == 403  # no self-escalation
    assert c.patch(f"/api/v1/admin/users/{ADMIN}/role", headers=H("admin"), json={"role": "learner"}).status_code == 400
    assert c.patch(f"/api/v1/admin/users/{L1}/role", headers=H("admin"), json={"role": "superuser"}).status_code == 422
    r = c.patch(f"/api/v1/admin/users/{L1}/role", headers=H("admin"), json={"role": "teacher"})
    assert r.status_code == 200 and r.json()["previous_role"] == "learner"
    ev = next(a for a in repo.audit if a["event_type"] == "admin.role_changed")
    assert ev["metadata"] == {"previous_role": "learner", "new_role": "teacher"} and ev["actor_id"] == ADMIN
    assert c.patch("/api/v1/admin/users/00000000-0000-4000-8000-0000000000ff/role", headers=H("admin"), json={"role": "teacher"}).status_code == 404


def test_admin_enrolment_and_assignment(env):
    c, repo, _ = env
    seed_learners(repo)
    repo.profiles[T1] = {"id": T1, "display_name": "T", "role": "teacher"}
    repo.enrollments.pop(L2, None)
    assert c.put(f"/api/v1/admin/courses/{CID}/enrollments/{L2}", headers=H("teacher")).status_code == 403
    assert c.put(f"/api/v1/admin/courses/{CID}/enrollments/{L2}", headers=H("admin")).status_code == 204
    assert c.get(f"/api/v1/lectures/{LID}", headers=H("learner2")).status_code == 200
    assert c.delete(f"/api/v1/admin/courses/{CID}/enrollments/{L2}", headers=H("admin")).status_code == 204
    assert c.get(f"/api/v1/lectures/{LID}", headers=H("learner2")).status_code == 404
    assert c.put(f"/api/v1/admin/courses/{CID}/teachers/{T1}/learners/{L2}", headers=H("admin")).status_code == 204
    assert repo.assignments[T1] == [L2]
    assert c.get(f"/api/v1/teacher/learners/{L2}/results", headers=H("teacher")).status_code == 200
    assert c.delete(f"/api/v1/admin/courses/{CID}/teachers/{T1}/learners/{L2}", headers=H("admin")).status_code == 204
    assert c.get(f"/api/v1/teacher/learners/{L2}/results", headers=H("teacher")).status_code == 404
    events = [a["event_type"] for a in repo.audit]
    assert {"admin.enrolled", "admin.unenrolled", "admin.teacher_assigned", "admin.teacher_unassigned"} <= set(events)
    assert c.put(f"/api/v1/admin/courses/{CID}/enrollments/{T1}", headers=H("admin")).status_code == 404  # a teacher is not a learner


# ---------- grader result validation (§9 step 8) ----------
def test_valid_grader_payload_is_accepted():
    g = validate_payload({"status": "passed", "passed_tests": 2, "total_tests": 2, "score": 100, "execution_ms": 5,
                          "feedback": [{"kind": "success", "message": "ok"}], "criteria": [{"test_order": 1, "passed": True}],
                          "grader_version": "1.1.0", "runtime_error": False})
    assert g.status == "passed" and g.score == 100 and g.grader_version == "1.1.0"


@pytest.mark.parametrize("bad", [
    None, [], {"status": "hacked"}, {"status": "passed", "score": 250}, {"status": "passed", "score": -1},
    {"status": "passed", "score": True}, {"status": "passed", "passed_tests": 5, "total_tests": 2},
    {"status": "passed", "feedback": "oops"}, {"status": "passed", "feedback": [{"message": 7}]},
    {"status": "passed", "criteria": [{"test_order": "1", "passed": True}]}, {"status": "passed", "execution_ms": -3},
    {"status": "passed", "feedback": [{"message": "x"}] * 51},
])
def test_malformed_grader_results_are_rejected(bad):
    with pytest.raises(InvalidGraderResult):
        validate_payload(bad)


def test_oversized_feedback_is_truncated():
    g = validate_payload({"status": "failed", "feedback": [{"kind": "failure", "message": "x" * 5000}]})
    assert len(g.feedback[0]["message"]) == 500
