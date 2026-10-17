import copy
import json
from pathlib import Path

from tests.conftest import H
from tests.fakes import CID

ROOT = Path(__file__).resolve().parents[2]
PACK = json.loads((ROOT / "content" / "lectures" / "010-numbers-text-fstrings.json").read_text())
SECRET = {"kind": "stdout_equals", "expected": "SECRET-ANSWER-60"}
TESTS = {t["key"]: SECRET for t in PACK["lab"]["tests"] if t.get("hidden")}  # visible checks carry their definition inline
URL = "/api/v1/admin/content/packs"


def prep(repo):
    repo.tables["modules"] = [{"id": "00000000-0000-4000-8000-000000000002", "course_id": CID, "sort_order": 1}]


def post(c, path, body, who="admin"):
    return c.post(f"{URL}/{path}", headers=H(who), json=body)


def test_only_admins_can_validate_or_import(env):
    c, repo, _ = env
    prep(repo)
    for who in ("learner1", "teacher"):
        assert post(c, "validate", {"pack": PACK, "tests": TESTS}, who).status_code == 403
        assert post(c, "import", {"pack": PACK, "tests": TESTS}, who).status_code == 403


def test_validate_reports_problems_and_missing_tests(env):
    c, repo, _ = env
    prep(repo)
    ok = post(c, "validate", {"pack": PACK, "tests": TESTS}).json()
    assert ok["valid"] and ok["summary"]["lecture_number"] == 10 and ok["missing_tests"] == []
    assert "SECRET-ANSWER" not in json.dumps(ok)
    r = post(c, "validate", {"pack": PACK, "tests": {}}).json()
    assert not r["valid"] and r["missing_tests"] == sorted(TESTS)  # inline-defined visible checks are never "missing"
    bad = copy.deepcopy(PACK)
    bad["checkpoints"][0]["question"]["correct_option_id"] = "z"
    r = post(c, "validate", {"pack": bad, "tests": TESTS}).json()
    assert not r["valid"] and any("correct_option_id" in p for p in r["problems"])


def test_import_writes_a_draft_and_is_idempotent(env):
    c, repo, _ = env
    prep(repo)
    r = post(c, "import", {"pack": PACK, "tests": TESTS})
    assert r.status_code == 200, r.text
    first = r.json()
    assert first["status"] == "draft" and first["created"] is True
    assert first["rows"] == {"lectures": 1, "mcq_questions": 3, "lecture_checkpoints": 3, "lecture_exercises": 1, "lecture_segments": 8, "exercise_tests": len(PACK["lab"]["tests"]), "lab_questions": 0}
    lecture = repo.content["lectures"][0]
    assert lecture["status"] == "draft" and lecture["published_at"] is None
    assert {q["status"] for q in repo.content["mcq_questions"]} == {"draft"}
    again = post(c, "import", {"pack": PACK, "tests": TESTS}).json()
    assert again["created"] is False and again["lecture_id"] == first["lecture_id"]
    assert len(repo.content["lecture_segments"]) == 8 and len(repo.content["mcq_questions"]) == 3


def test_hidden_definitions_are_stored_but_never_returned_or_audited(env):
    c, repo, _ = env
    prep(repo)
    r = post(c, "import", {"pack": PACK, "tests": TESTS})
    assert "SECRET-ANSWER" not in r.text
    hidden = [t for t in repo.content["exercise_tests"] if t["is_hidden"]]
    assert hidden and {t["definition"]["expected"] for t in hidden} == {"SECRET-ANSWER-60"}
    assert all("SECRET" not in json.dumps(t["definition"]) for t in repo.content["exercise_tests"] if not t["is_hidden"])
    assert "SECRET-ANSWER" not in json.dumps(repo.audit)
    assert any(a["event_type"] == "admin.content_pack_imported" for a in repo.audit)
    listing = c.get("/api/v1/admin/audit", headers=H("admin"))
    assert "SECRET-ANSWER" not in listing.text


def test_invalid_or_incomplete_imports_write_nothing(env):
    c, repo, _ = env
    prep(repo)
    bad = copy.deepcopy(PACK)
    bad["segments"].pop()
    assert post(c, "import", {"pack": bad, "tests": TESTS}).status_code == 422
    assert post(c, "import", {"pack": PACK, "tests": {}}).status_code == 422
    assert repo.content == {}


def test_published_lecture_is_protected_from_a_draft_import(env):
    c, repo, _ = env
    prep(repo)
    post(c, "import", {"pack": PACK, "tests": TESTS, "publish": True})
    assert repo.content["lectures"][0]["status"] == "published"
    blocked = post(c, "import", {"pack": PACK, "tests": TESTS})
    assert blocked.status_code == 409 and repo.content["lectures"][0]["status"] == "published"
    forced = post(c, "import", {"pack": PACK, "tests": TESTS, "replace_published": True})
    assert forced.status_code == 200 and repo.content["lectures"][0]["status"] == "draft"


def test_publishing_through_the_status_endpoint_publishes_questions_and_lab(env):
    c, repo, _ = env
    prep(repo)
    lid = post(c, "import", {"pack": PACK, "tests": TESTS}).json()["lecture_id"]
    r = c.patch(f"/api/v1/admin/lectures/{lid}/status", headers=H("admin"), json={"status": "published"})
    assert r.status_code == 200, r.text
    assert {q["status"] for q in repo.content["mcq_questions"]} == {"published"}
    assert {e["status"] for e in repo.content["lecture_exercises"]} == {"published"}
    c.patch(f"/api/v1/admin/lectures/{lid}/status", headers=H("admin"), json={"status": "draft"})
    assert {q["status"] for q in repo.content["mcq_questions"]} == {"draft"}


def test_prerequisites_resolve_to_existing_lectures(env):
    c, repo, _ = env
    prep(repo)
    pack11 = json.loads((ROOT / "content" / "lectures" / "011-decisions-with-if.json").read_text())
    tests = {t["key"]: SECRET for t in pack11["lab"]["tests"] if t.get("hidden")}
    post(c, "import", {"pack": PACK, "tests": TESTS})
    post(c, "import", {"pack": pack11, "tests": tests})
    ten = next(x for x in repo.content["lectures"] if x["lecture_number"] == 10)
    eleven = next(x for x in repo.content["lectures"] if x["lecture_number"] == 11)
    assert eleven["prerequisites"] == [ten["id"]]


def test_oversized_pack_is_rejected(env):
    c, repo, _ = env
    prep(repo)
    big = copy.deepcopy(PACK)
    big["segments"][0]["body"] = "x" * 500_000
    assert post(c, "validate", {"pack": big, "tests": TESTS}).status_code == 413
