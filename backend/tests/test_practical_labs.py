"""Practical Labs: listing and states, hint cycles + Redo, quiz marking, written/upload review flow, admin test visibility,
worker claim payload, pack schema v2."""
import json
import uuid

import pytest

from app.content_pack import build_rows, check_pack
from tests.conftest import H
from tests.fakes import CP1, CP2, CP3, EX, LID, Q1, Q2, Q3
from tests.test_worker_queue import CAPS

L1 = "11111111-1111-4111-8111-111111111111"
L2 = "22222222-2222-4222-8222-222222222222"
T1 = "33333333-3333-4333-8333-333333333333"
W = {"X-Worker-Token": "test-worker-token"}


def key():
    return str(uuid.uuid4())


def answer(c, cp, q, opt, who="learner1"):
    r = c.post(f"/api/v1/checkpoints/{cp}/attempts", headers=H(who, key()), json={"question_id": q, "selected_option_id": opt})
    assert r.status_code == 200, r.text


def reach_lab(c, who="learner1"):
    c.get(f"/api/v1/lectures/{LID}/session", headers=H(who))
    answer(c, CP1, Q1, "b", who)
    answer(c, CP2, Q2, "a", who)


def make_pass_fail(repo, **extra):
    repo.d["exercise"].update({"scoring": "pass_fail", "pass_threshold": 100, "hint_penalty_percent": 0, "hints_max": 3, **extra})


def submit(c, who="learner1", **body):
    return c.post(f"/api/v1/exercises/{EX}/submissions", headers=H(who, key()), json=body)


# ---------------- listing
def test_labs_listing_shows_each_lecture_lab_with_a_server_decided_state(env):
    c, repo, grader = env
    r = c.get("/api/v1/labs", headers=H("learner1"))
    assert r.status_code == 200, r.text
    course = r.json()["courses"][0]
    lab = course["modules"][0]["labs"][0]
    assert lab["lecture_number"] == 9 and lab["lab_kind"] == "code" and lab["state"] == "not_started" and course["passed"] == 0
    reach_lab(c)
    submit(c, source_code="BAD")
    assert c.get("/api/v1/labs", headers=H("learner1")).json()["courses"][0]["modules"][0]["labs"][0]["state"] == "needs_retry"
    submit(c, source_code="GOOD")
    after = c.get("/api/v1/labs", headers=H("learner1")).json()["courses"][0]
    assert after["modules"][0]["labs"][0]["state"] == "passed" and after["passed"] == 1
    # a learner who is not enrolled sees nothing; a teacher sees the catalogue
    repo.enrollments[L2] = set()
    assert c.get("/api/v1/labs", headers=H("learner2")).json()["courses"] == []
    assert c.get("/api/v1/labs", headers=H("teacher")).json()["courses"][0]["modules"][0]["labs"][0]["state"] == "not_started"


def test_locked_lecture_gives_a_locked_lab(env):
    c, repo, _ = env
    repo.d["lecture"]["prerequisites"] = ["00000000-0000-4000-8000-000000000008"]
    lab = c.get("/api/v1/labs", headers=H("learner1")).json()["courses"][0]["modules"][0]["labs"][0]
    assert lab["state"] == "locked" and lab["lecture_state"] == "locked"
    assert c.get(f"/api/v1/exercises/{EX}", headers=H("learner1")).status_code == 400


# ---------------- hints per cycle + redo
def test_pass_fail_lab_caps_hints_per_cycle_and_redo_resets_them(env):
    c, repo, _ = env
    make_pass_fail(repo, hints_max=2)
    reach_lab(c)
    ex = c.get(f"/api/v1/exercises/{EX}", headers=H("learner1")).json()
    assert ex["scoring"] == "pass_fail" and ex["hints_max"] == 2 and ex["hints_used"] == 0 and ex["cycle"] == 1 and ex["redo_available"] is False
    assert "Redo" in ex["hints_policy"]
    hint = lambda i: c.post(f"/api/v1/exercises/{EX}/hints", headers=H("learner1"), json={"hint_index": i})  # noqa: E731
    assert hint(0).status_code == 200 and hint(1).status_code == 200
    third = hint(2)
    assert third.status_code == 409 and third.json()["error"]["code"] == "HINTS_EXHAUSTED"
    # hints do NOT reset when a new attempt is made (they are per cycle)
    submit(c, source_code="BAD")
    ex = c.get(f"/api/v1/exercises/{EX}", headers=H("learner1")).json()
    assert ex["hints_used"] == 2 and ex["redo_available"] is True and len(ex["hints_revealed"]) == 2
    c.put(f"/api/v1/exercises/{EX}/draft", headers=H("learner1"), json={"source_code": "work in progress"})
    r = c.post(f"/api/v1/exercises/{EX}/redo", headers=H("learner1"))
    assert r.status_code == 200 and r.json() == {"cycle": 2, "redo_count": 1, "hints_used": 0, "hints_max": 2, "starter_code": "x=1"}
    ex = c.get(f"/api/v1/exercises/{EX}", headers=H("learner1")).json()
    assert ex["hints_used"] == 0 and ex["cycle"] == 2 and ex["redo_count"] == 1 and ex["draft"] is None and ex["attempts_used"] == 1
    assert hint(0).status_code == 200  # fresh hints in the new cycle
    assert any(a["event_type"] == "lab.redo" for a in repo.audit)


def test_redo_is_refused_before_the_hints_are_used_and_on_score_mode_labs(env):
    c, repo, _ = env
    reach_lab(c)
    r = c.post(f"/api/v1/exercises/{EX}/redo", headers=H("learner1"))
    assert r.status_code == 409 and r.json()["error"]["code"] == "REDO_NOT_AVAILABLE"
    make_pass_fail(repo)
    r = c.post(f"/api/v1/exercises/{EX}/redo", headers=H("learner1"))
    assert r.status_code == 409


def test_score_mode_hints_still_reset_per_attempt_with_a_penalty(env):
    c, repo, _ = env
    reach_lab(c)
    assert c.post(f"/api/v1/exercises/{EX}/hints", headers=H("learner1"), json={"hint_index": 0}).status_code == 200
    submit(c, source_code="GOOD")
    ex = c.get(f"/api/v1/exercises/{EX}", headers=H("learner1")).json()
    assert ex["hints_revealed"] == [] and ex["scoring"] == "score"


# ---------------- quiz
QUESTIONS = [
    {"id": "q-1", "exercise_id": EX, "question_order": 1, "prompt": "2+2?", "options": [{"id": "a", "text": "4"}, {"id": "b", "text": "5"}], "correct_option_id": "a", "explanation": "Two and two make four.", "points": 1},
    {"id": "q-2", "exercise_id": EX, "question_order": 2, "prompt": "Capital of Kenya?", "options": [{"id": "a", "text": "Lagos"}, {"id": "b", "text": "Nairobi"}], "correct_option_id": "b", "explanation": "Nairobi.", "points": 1},
    {"id": "q-3", "exercise_id": EX, "question_order": 3, "prompt": "AI subset?", "options": [{"id": "a", "text": "ML"}, {"id": "b", "text": "Excel"}], "correct_option_id": "a", "explanation": "ML sits inside AI.", "points": 1},
]


def test_quiz_lab_is_marked_on_the_server_without_revealing_answers(env):
    c, repo, _ = env
    make_pass_fail(repo, lab_kind="quiz")
    repo.questions_by_exercise[EX] = QUESTIONS
    reach_lab(c)
    ex = c.get(f"/api/v1/exercises/{EX}", headers=H("learner1")).json()
    assert ex["lab_kind"] == "quiz" and len(ex["questions"]) == 3 and "correct" not in json.dumps(ex["questions"])
    assert submit(c, answers={}).status_code == 422
    r = submit(c, answers={"q-1": "a", "q-2": "a", "q-3": "a"})
    assert r.status_code == 202 and r.json()["status"] == "failed"
    v = c.get(f"/api/v1/submissions/{r.json()['submission_id']}", headers=H("learner1")).json()
    assert v["passed_tests"] == 2 and v["total_tests"] == 3 and [q["correct"] for q in v["quiz_results"]] == [True, False, True]
    assert v["quiz_results"][1]["explanation"] == "Nairobi." and "correct_option_id" not in json.dumps(v)
    assert v["criteria"][1]["passed"] is False and [m["text"] for m in v["remediation"]] == ["Nairobi."]
    r = submit(c, answers={"q-1": "a", "q-2": "b", "q-3": "a"})
    assert r.json()["status"] == "passed"
    assert c.get("/api/v1/labs", headers=H("learner1")).json()["courses"][0]["modules"][0]["labs"][0]["state"] == "passed"
    answer(c, CP3, Q3, "c")
    assert c.post(f"/api/v1/lectures/{LID}/complete", headers=H("learner1")).status_code == 200  # a passed quiz completes the lab gate


# ---------------- written + upload with teacher review
RUBRIC = [{"criterion": "Names the problem", "description": "...", "max_points": 2}, {"criterion": "Gives evidence", "description": "...", "max_points": 3}]


def test_written_lab_goes_to_the_assigned_teacher_whose_review_becomes_the_official_result(env):
    c, repo, _ = env
    make_pass_fail(repo, lab_kind="written", rubric=RUBRIC)
    repo.profiles.update({L1: {"id": L1, "display_name": "Asha", "role": "learner"}})
    repo.assignments[T1] = [L1]
    reach_lab(c)
    assert submit(c, source_code="").status_code == 422
    r = submit(c, source_code="I audited three apps and found two AI features: ...")
    assert r.status_code == 202 and r.json()["status"] == "submitted"
    sid = r.json()["submission_id"]
    v = c.get(f"/api/v1/submissions/{sid}", headers=H("learner1")).json()
    assert v["awaiting_review"] is True and v["review"] is None
    assert c.get("/api/v1/labs", headers=H("learner1")).json()["courses"][0]["modules"][0]["labs"][0]["state"] == "awaiting_review"
    # the queue: assigned teacher sees it, an unassigned teacher does not, a learner cannot look
    pending = c.get("/api/v1/teacher/reviews", headers=H("teacher")).json()
    assert pending["total"] == 1 and pending["pending"][0]["learner"] == "Asha" and pending["pending"][0]["submission_id"] == sid
    repo.assignments[T1] = []
    assert c.get("/api/v1/teacher/reviews", headers=H("teacher")).json()["total"] == 0
    assert c.post(f"/api/v1/teacher/submissions/{sid}/review", headers=H("teacher"), json={"passed": True, "feedback": "x"}).status_code == 404
    assert c.get("/api/v1/teacher/reviews", headers=H("learner1")).status_code == 403
    repo.assignments[T1] = [L1]
    bad = c.post(f"/api/v1/teacher/submissions/{sid}/review", headers=H("teacher"), json={"passed": True, "feedback": "ok", "scores": [{"criterion": "Gives evidence", "points": 9}]})
    assert bad.status_code == 422
    r = c.post(f"/api/v1/teacher/submissions/{sid}/review", headers=H("teacher"),
               json={"passed": True, "feedback": "Clear audit, good evidence.", "scores": [{"criterion": "Names the problem", "points": 2}, {"criterion": "Gives evidence", "points": 2}]})
    assert r.status_code == 200 and r.json()["status"] == "passed" and r.json()["score"] == 80
    v = c.get(f"/api/v1/submissions/{sid}", headers=H("learner1")).json()
    assert v["status"] == "passed" and v["review"]["feedback"] == "Clear audit, good evidence." and v["awaiting_review"] is False
    ex = c.get(f"/api/v1/exercises/{EX}", headers=H("learner1")).json()
    assert ex["review"]["passed"] is True and ex["rubric"] == RUBRIC
    detail = c.get(f"/api/v1/teacher/submissions/{sid}", headers=H("teacher")).json()
    assert detail["lab_kind"] == "written" and detail["review"]["scores"][0]["points"] == 2
    assert any(a["event_type"] == "teacher.reviewed" for a in repo.audit)
    answer(c, CP3, Q3, "c")
    assert c.post(f"/api/v1/lectures/{LID}/complete", headers=H("learner1")).status_code == 200


def test_review_is_refused_for_code_labs(env):
    c, repo, _ = env
    reach_lab(c)
    sid = submit(c, source_code="GOOD").json()["submission_id"]
    repo.assignments[T1] = [L1]
    r = c.post(f"/api/v1/teacher/submissions/{sid}/review", headers=H("teacher"), json={"passed": False, "feedback": "no"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "NOT_REVIEWABLE"


def test_upload_lab_validates_link_and_checklist(env):
    c, repo, _ = env
    make_pass_fail(repo, lab_kind="upload", rubric=RUBRIC, checklist=["Deployed", "README present"])
    reach_lab(c)
    r = submit(c, answers={"link": "ftp://x", "checklist": [True, False]})
    assert r.status_code == 422
    issues = {d["field"] for d in r.json()["error"]["details"]}
    assert issues == {"link", "checklist"}
    r = submit(c, answers={"link": "https://github.com/asha/capstone", "notes": "Deployed on the free tier.", "checklist": [True, True]})
    assert r.status_code == 202 and r.json()["status"] == "submitted"
    v = c.get(f"/api/v1/submissions/{r.json()['submission_id']}", headers=H("learner1")).json()
    assert v["answers"] == {"link": "https://github.com/asha/capstone", "notes": "Deployed on the free tier.", "checklist": [True, True]}


# ---------------- admin visibility + worker payload
def test_admin_can_always_see_every_test_definition_and_quiz_answer(env):
    c, repo, _ = env
    repo.questions_by_exercise[EX] = QUESTIONS
    assert c.get(f"/api/v1/admin/exercises/{EX}/tests", headers=H("teacher")).status_code == 403
    r = c.get(f"/api/v1/admin/exercises/{EX}/tests", headers=H("admin"))
    assert r.status_code == 200
    assert r.json()["tests"][0] == {"test_order": 1, "hidden": True, "label": "SECRET-LABEL", "definition": {"secret": "HIDDEN-EXPECTED"}, "points": 1.0,
                                    "remediation": "Review how print works.", "objective": "Print output"}
    assert r.json()["questions"][1]["correct_option_id"] == "b"
    assert c.get(f"/api/v1/admin/exercises/{uuid.uuid4()}/tests", headers=H("admin")).status_code == 404


def test_learner_view_never_includes_hidden_definitions(env):
    c, repo, _ = env
    reach_lab(c)
    ex = c.get(f"/api/v1/exercises/{EX}", headers=H("learner1")).json()
    assert [v["test_order"] for v in ex["visible_checks"]] == [2] and "HIDDEN-EXPECTED" not in json.dumps(ex)


def test_worker_claim_carries_files_limits_and_packages(env, monkeypatch):
    c, repo, _ = env
    monkeypatch.setenv("GRADER_MODE", "queue")
    monkeypatch.setenv("GRADER_WORKER_TOKEN", "test-worker-token")
    repo.d["exercise"].update({"packages": ["pandas", "requests"], "assets": [{"name": "marks.csv", "content": "a,b\n1,2\n"}, {"name": "img.png", "encoding": "base64", "content": "AAEC"}],
                               "limits": {"timeout_seconds": 12}})
    reach_lab(c)
    submit(c, source_code="import pandas")
    job = c.post("/api/v1/internal/grader/claim", headers=W, json={"worker_id": "w-1", **CAPS}).json()
    assert job["packages"] == ["pandas", "requests"] and job["files"] == {"marks.csv": "a,b\n1,2\n", "img.png": {"encoding": "base64", "content": "AAEC"}}
    assert job["limits"] == {"memory_mb": 384, "timeout_seconds": 12.0} and job["timeout_seconds"] == 12.0


# ---------------- pack schema v2
def base_pack(**lab):
    return {"schema_version": 2, "lecture_number": 30, "title": "Regression", "summary": "Fit a line to study hours and scores.", "objectives": ["Fit a model"],
            "duration_minutes": 60, "prerequisites": [29], "lab_only": True,
            "segments": [{"key": "intro", "type": "intro", "title": "What you will build", "body": "Today you fit a regression model on a small dataset."},
                         {"key": "lab", "type": "exercise", "title": "Lab: regression"}],
            "lab": {"title": "Fit a regression", "objective": "Predict a score from study hours.", "instructions": "Load hours.csv, fit LinearRegression, predict for 6 hours.",
                    "success_criteria": ["A model is fitted", "A prediction is printed"], **lab}}


def test_code_pack_with_packages_assets_and_inline_visible_checks():
    pack, errs = check_pack(base_pack(kind="code", packages=["pandas", "scikit-learn"], starter_code="import pandas as pd\n",
                                      assets=[{"name": "hours.csv", "content": "hours,score\n1,50\n2,60\n3,70\n"}], limits={"timeout_seconds": 20},
                                      hints=["Read the CSV with pd.read_csv('hours.csv')."], solution="import pandas as pd\nprint(1)\n",
                                      tests=[{"key": "t1", "label": "Prints something", "remediation": "Add a print.", "objective": "Output", "definition": {"match": "non_empty"}},
                                             {"key": "t2", "remediation": "Fit the model on hours and score.", "objective": "Regression", "hidden": True}]))
    assert errs == [], errs
    rows = build_rows(pack, {"t2": {"expr": "round(float(model.predict([[6]])[0]))", "expected": 100}}, course_id="c", module_id="m")
    ex = rows["lecture_exercises"][0]
    assert ex["lab_kind"] == "code" and ex["scoring"] == "pass_fail" and ex["pass_threshold"] == 100 and ex["packages"] == ["pandas", "scikit-learn"]
    assert ex["assets"][0]["name"] == "hours.csv" and ex["limits"] == {"timeout_seconds": 20.0} and ex["hints_max"] == 3 and ex["hint_penalty_percent"] == 0
    assert rows["exercise_tests"][0]["definition"] == {"match": "non_empty"} and rows["exercise_tests"][1]["definition"]["expected"] == 100
    assert rows["lab_questions"] == [] and rows["lecture_checkpoints"] == [] and len(rows["lecture_segments"]) == 2
    assert "solution" not in json.dumps(rows)


def test_code_pack_requires_solution_hints_and_a_hidden_check():
    _, errs = check_pack(base_pack(kind="code", tests=[{"key": "t1", "remediation": "Add a print.", "objective": "Output", "definition": {"match": "non_empty"}},
                                                      {"key": "t2", "remediation": "Fit it.", "objective": "Regression", "hidden": True}], hints=["h"]))
    assert any("reference solution" in e for e in errs)
    _, errs = check_pack(base_pack(kind="code", solution="x", hints=["h"], tests=[{"key": "t1", "remediation": "Add a print.", "objective": "Output"}]))
    assert any("at least two checks" in e for e in errs)


def test_quiz_written_and_upload_packs():
    q = {"prompt": "Which is AI?", "options": [{"id": "a", "text": "Spam filter"}, {"id": "b", "text": "Calculator"}], "correct_option_id": "a", "explanation": "It learns from data."}
    pack, errs = check_pack(base_pack(kind="quiz", questions=[q, {**q, "prompt": "Second?"}, {**q, "prompt": "Third?"}]))
    assert errs == [] and build_rows(pack, {}, course_id="c", module_id="m")["lab_questions"][2]["question_order"] == 3
    _, errs = check_pack(base_pack(kind="quiz", questions=[q]))
    assert any("three questions" in e for e in errs)
    pack, errs = check_pack(base_pack(kind="written", rubric=[{"criterion": "Problem", "description": "States it", "max_points": 2}, {"criterion": "Evidence", "description": "Gives it", "max_points": 3}]))
    assert errs == [] and build_rows(pack, {}, course_id="c", module_id="m")["lecture_exercises"][0]["rubric"][1]["max_points"] == 3
    _, errs = check_pack(base_pack(kind="upload", rubric=[{"criterion": "Alpha", "description": "aaaaa", "max_points": 1}, {"criterion": "Bravo", "description": "bbbbb", "max_points": 1}]))
    assert any("checklist" in e for e in errs)
    pack, errs = check_pack(base_pack(kind="upload", checklist=["Deployed", "README"], rubric=[{"criterion": "Alpha", "description": "aaaaa"}, {"criterion": "Bravo", "description": "bbbbb"}]))
    assert errs == [] and build_rows(pack, {}, course_id="c", module_id="m")["lecture_exercises"][0]["checklist"] == ["Deployed", "README"]


def test_lab_only_pack_cannot_carry_checkpoints_and_full_pack_still_needs_exit_check():
    rubric = [{"criterion": "Alpha", "description": "aaaaa"}, {"criterion": "Bravo", "description": "bbbbb"}]
    p = base_pack(kind="written", rubric=rubric)
    p["segments"].append({"key": "exit", "type": "exit_check", "title": "Exit", "checkpoint": "cp1"})
    _, errs = check_pack(p)
    assert errs and any("checkpoint" in e for e in errs)
    p = base_pack(kind="written", rubric=rubric)
    p["lab_only"] = False
    _, errs = check_pack(p)
    assert any("checkpoint" in e for e in errs)


def test_schema_v1_pack_with_explicit_score_mode_still_validates():
    from pathlib import Path
    pack, errs = check_pack(json.loads((Path(__file__).parent / "fixtures" / "v1_pack_010.json").read_text()))
    assert errs == [] and pack.schema_version == 1 and pack.lab.kind == "code"
    assert pack.lab.scoring == "score" and pack.lab.effective_threshold == 80 and pack.lab.hints_max == 3


@pytest.mark.parametrize("name", ["009-python-setup-first-program.json", "010-numbers-text-fstrings.json", "011-decisions-with-if.json", "012-lists-and-loops.json"])
def test_block1_lecture_packs_are_pass_fail_labs_with_visible_checks_inline(name):
    from pathlib import Path
    pack, errs = check_pack(json.loads((Path(__file__).resolve().parents[2] / "content" / "lectures" / name).read_text()))
    assert errs == [] and pack.lab.scoring == "pass_fail" and pack.lab.kind == "code" and not pack.lab_only
    assert all(t.definition is not None for t in pack.lab.tests if not t.hidden)
    assert all(t.definition is None for t in pack.lab.tests if t.hidden)
