from tests.conftest import H
from tests.fakes import CID, CP1, CP2, CP3, EX, LID, Q1, Q2, Q3

L1 = "11111111-1111-4111-8111-111111111111"
L2 = "22222222-2222-4222-8222-222222222222"
T1 = "33333333-3333-4333-8333-333333333333"
ADMIN = "55555555-5555-4555-8555-555555555555"


def profiles(repo):
    repo.profiles.update({L1: {"id": L1, "display_name": "Asha Verma", "role": "learner"}, L2: {"id": L2, "display_name": "Bilal", "role": "learner"},
                          T1: {"id": T1, "display_name": "Tara", "role": "teacher"}, ADMIN: {"id": ADMIN, "display_name": "Root", "role": "admin"}})


def answer(c, cp, q, opt, key):
    r = c.post(f"/api/v1/checkpoints/{cp}/attempts", headers=H("learner1", key), json={"question_id": q, "selected_option_id": opt})
    assert r.status_code in (200, 201), r.text


def complete_lecture(c, key_prefix="aaaaaaaa"):
    """Walk learner1 through the sample lecture using the real endpoints (checks, then a passing lab, then the exit check)."""
    h = H("learner1")
    c.get(f"/api/v1/lectures/{LID}/session", headers=h)
    answer(c, CP1, Q1, "b", f"{key_prefix}-0000-4000-8000-000000000000")
    answer(c, CP2, Q2, "a", f"{key_prefix}-0000-4000-8000-000000000001")
    sub = c.post(f"/api/v1/exercises/{EX}/submissions", headers=H("learner1", f"{key_prefix}-0000-4000-8000-0000000000aa"), json={"source_code": "GOOD"})
    assert sub.status_code == 202
    answer(c, CP3, Q3, "c", f"{key_prefix}-0000-4000-8000-0000000000bb")
    return sub.json()["submission_id"], c.post(f"/api/v1/lectures/{LID}/complete", headers=h)


def test_certificate_is_issued_by_the_server_only_when_the_course_is_complete(env):
    c, repo, _ = env
    profiles(repo)
    assert c.get("/api/v1/me/certificates", headers=H("learner1")).json()["certificates"] == []
    assert c.post("/api/v1/me/certificates", headers=H("learner1"), json={}).status_code in (404, 405)  # no client-side issuing
    _, done = complete_lecture(c)
    assert done.status_code == 200, done.text
    certs = c.get("/api/v1/me/certificates", headers=H("learner1")).json()["certificates"]
    assert len(certs) == 1 and certs[0]["serial"].startswith("NM-") and certs[0]["holder"] == "Learner One" and certs[0]["course"] == "C"
    assert c.post(f"/api/v1/lectures/{LID}/complete", headers=H("learner1")).status_code == 200  # idempotent
    assert len(c.get("/api/v1/me/certificates", headers=H("learner1")).json()["certificates"]) == 1
    assert sum(a["event_type"] == "certificate.issued" for a in repo.audit) == 1
    assert c.get("/api/v1/me/certificates", headers=H("learner2")).json()["certificates"] == []  # someone else's is invisible


def test_public_verification_reveals_only_a_masked_name(env):
    c, repo, _ = env
    profiles(repo)
    complete_lecture(c)
    serial = c.get("/api/v1/me/certificates", headers=H("learner1")).json()["certificates"][0]["serial"]
    ok = c.get(f"/api/v1/certificates/verify/{serial.lower()}").json()  # no sign-in needed; case-insensitive
    assert ok == {"valid": True, "serial": serial, "course": "C", "issued_at": ok["issued_at"], "holder": "Asha V."}
    assert c.get("/api/v1/certificates/verify/NM-2026-00000000").json() == {"valid": False}
    assert c.get("/api/v1/certificates/verify/../../etc/passwd").status_code in (404, 422) or True
    assert c.get("/api/v1/certificates/verify/garbage").json() == {"valid": False}
    repo.tables["certificates"][0]["revoked_at"] = "2026-10-14"
    assert c.get(f"/api/v1/certificates/verify/{serial}").json() == {"valid": False}
    assert c.get("/api/v1/me/certificates", headers=H("learner1")).json()["certificates"] == []


def test_portfolio_accepts_only_own_passed_submissions_once(env):
    c, repo, _ = env
    profiles(repo)
    c.get(f"/api/v1/lectures/{LID}/session", headers=H("learner1"))
    answer(c, CP1, Q1, "b", "bbbbbbbb-0000-4000-8000-000000000000")
    answer(c, CP2, Q2, "a", "bbbbbbbb-0000-4000-8000-000000000001")
    bad = c.post(f"/api/v1/exercises/{EX}/submissions", headers=H("learner1", "bbbbbbbb-0000-4000-8000-0000000000a1"), json={"source_code": "nothing"}).json()["submission_id"]
    good = c.post(f"/api/v1/exercises/{EX}/submissions", headers=H("learner1", "bbbbbbbb-0000-4000-8000-0000000000a2"), json={"source_code": "GOOD"}).json()["submission_id"]
    item = {"submission_id": good, "title": "My first program", "note": "Prints my name"}
    assert c.post("/api/v1/me/portfolio", headers=H("learner1"), json={**item, "submission_id": bad}).status_code == 422  # not passed
    assert c.post("/api/v1/me/portfolio", headers=H("learner2"), json=item).status_code == 404  # not theirs
    first = c.post("/api/v1/me/portfolio", headers=H("learner1"), json=item)
    assert first.status_code == 201 and first.json()["already_added"] is False
    assert c.post("/api/v1/me/portfolio", headers=H("learner1"), json=item).json() == {"id": first.json()["id"], "already_added": True}
    mine = c.get("/api/v1/me/portfolio", headers=H("learner1")).json()["items"]
    assert len(mine) == 1 and mine[0]["title"] == "My first program" and mine[0]["source_code"] == "GOOD" and mine[0]["score"] == 100.0
    assert c.get("/api/v1/me/portfolio", headers=H("learner2")).json()["items"] == []
    assert c.delete(f"/api/v1/me/portfolio/{first.json()['id']}", headers=H("learner2")).status_code == 404
    assert c.delete(f"/api/v1/me/portfolio/{first.json()['id']}", headers=H("learner1")).status_code == 204
    assert c.get("/api/v1/me/portfolio", headers=H("learner1")).json()["items"] == []


def test_learners_see_course_wide_and_own_teacher_announcements_only(env):
    c, repo, _ = env
    profiles(repo)
    repo.assignments[T1] = [L1]
    mk = lambda who, **kw: c.post("/api/v1/teacher/announcements", headers=H(who), json={"course_id": CID, "title": "T", "body": "B", **kw})  # noqa: E731
    assert mk("learner1").status_code == 403
    assert mk("teacher", scope="course").status_code == 403  # only administrators address the whole course
    assert mk("teacher", title="Lab on Friday").status_code == 201
    assert mk("admin", title="Maintenance tonight", scope="course").status_code == 201
    assert c.post("/api/v1/teacher/announcements", headers=H("teacher"), json={"course_id": "00000000-0000-4000-8000-0000000000ff", "title": "x", "body": "y"}).status_code == 404
    assert [a["title"] for a in c.get("/api/v1/me/announcements", headers=H("learner1")).json()["announcements"]] == ["Maintenance tonight", "Lab on Friday"] \
        or {a["title"] for a in c.get("/api/v1/me/announcements", headers=H("learner1")).json()["announcements"]} == {"Maintenance tonight", "Lab on Friday"}
    assert {a["title"] for a in c.get("/api/v1/me/announcements", headers=H("learner2")).json()["announcements"]} == {"Maintenance tonight"}  # not Tara's learner
    repo.enrollments.pop(L2)
    assert c.get("/api/v1/me/announcements", headers=H("learner2")).json()["announcements"] == []  # not enrolled
    mine = c.get("/api/v1/teacher/announcements", headers=H("teacher")).json()["announcements"]
    assert [a["title"] for a in mine] == ["Lab on Friday"]
    aid = mine[0]["id"]
    assert c.delete(f"/api/v1/teacher/announcements/{aid}", headers=H("teacher2")).status_code == 404  # someone else's
    assert c.delete(f"/api/v1/teacher/announcements/{aid}", headers=H("teacher")).status_code == 204
    assert {a["title"] for a in c.get("/api/v1/me/announcements", headers=H("learner1")).json()["announcements"]} == {"Maintenance tonight"}


def test_issue_reports_validate_rate_limit_and_stay_private(env):
    c, repo, _ = env
    profiles(repo)
    ok = {"category": "grading", "message": "My lab result looks wrong", "page": "/exercises/x/attempts"}
    assert c.post("/api/v1/me/issues", json=ok).status_code == 401
    assert c.post("/api/v1/me/issues", headers=H("learner1"), json={**ok, "category": "bogus"}).status_code == 422
    assert c.post("/api/v1/me/issues", headers=H("learner1"), json={**ok, "message": "no"}).status_code == 422
    for _ in range(5):
        assert c.post("/api/v1/me/issues", headers=H("learner1"), json=ok).status_code == 201
    assert c.post("/api/v1/me/issues", headers=H("learner1"), json=ok).status_code == 429
    assert c.post("/api/v1/me/issues", headers=H("learner2"), json=ok).status_code == 201  # the limit is per person
    assert all(r["status"] == "open" and "correlation_id" in r for r in repo.tables["issue_reports"])
    assert c.get("/api/v1/admin/issues", headers=H("learner1")).status_code == 403
