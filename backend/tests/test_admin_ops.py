from datetime import UTC, datetime, timedelta

from tests.conftest import H
from tests.fakes import CID, EX, LID

L1 = "11111111-1111-4111-8111-111111111111"
L2 = "22222222-2222-4222-8222-222222222222"
T1 = "33333333-3333-4333-8333-333333333333"
T2 = "44444444-4444-4444-8444-444444444444"
ADMIN = "55555555-5555-4555-8555-555555555555"


def seed(repo):
    repo.profiles.update({
        L1: {"id": L1, "display_name": "Asha", "role": "learner", "created_at": "2026-01-01"},
        L2: {"id": L2, "display_name": "Bilal", "role": "learner", "created_at": "2026-01-02"},
        T1: {"id": T1, "display_name": "Tara", "role": "teacher", "created_at": "2026-01-03"},
        T2: {"id": T2, "display_name": "Tomas", "role": "teacher", "created_at": "2026-01-04"},
        ADMIN: {"id": ADMIN, "display_name": "Root", "role": "admin", "created_at": "2026-01-05"}})


def test_every_admin_endpoint_rejects_non_admins(env):
    c, repo, _ = env
    seed(repo)
    for who in ("learner1", "teacher"):
        for method, path in [("get", "/users"), ("get", "/overview"), ("get", "/queue"), ("get", "/audit"), ("get", "/courses"),
                             ("get", "/cohorts"), ("get", "/issues"), ("get", "/settings")]:
            assert getattr(c, method)(f"/api/v1/admin{path}", headers=H(who)).status_code == 403, (who, path)
        assert c.post("/api/v1/admin/users", headers=H(who), json={}).status_code == 403
        assert c.post(f"/api/v1/admin/users/{L1}/deactivate", headers=H(who)).status_code == 403
    assert c.get("/api/v1/admin/users").status_code == 401


def test_user_list_search_filters_and_create_deactivate_roundtrip(admin_env):
    c, repo, auth = admin_env
    seed(repo)
    auth.users.update({u: {"id": u, "email": f"{n}@x.test", "last_sign_in_at": None, "created_at": "x", "banned_until": None, "email_confirmed": True}
                       for u, n in [(L1, "asha"), (L2, "bilal"), (T1, "tara")]})
    r = c.get("/api/v1/admin/users", headers=H("admin")).json()
    assert r["total"] == 3 and {u["email"] for u in r["users"]} == {"asha@x.test", "bilal@x.test", "tara@x.test"}
    assert [u["display_name"] for u in c.get("/api/v1/admin/users?role=teacher", headers=H("admin")).json()["users"]] == ["Tara"]
    assert [u["display_name"] for u in c.get("/api/v1/admin/users?q=BIL", headers=H("admin")).json()["users"]] == ["Bilal"]

    body = {"email": "New.Person@x.test", "display_name": "New Person", "role": "learner", "password": "a-long-password-1", "course_id": CID}
    assert c.post("/api/v1/admin/users", headers=H("admin"), json={**body, "password": "short"}).status_code == 422
    assert c.post("/api/v1/admin/users", headers=H("admin"), json={**body, "email": "not-an-email"}).status_code == 422
    made = c.post("/api/v1/admin/users", headers=H("admin"), json=body)
    assert made.status_code == 201 and made.json()["email"] == "new.person@x.test"
    new_id = made.json()["id"]
    repo.profiles[new_id] = {"id": new_id, "display_name": "x", "role": "learner", "created_at": "x"}  # the database trigger creates this row
    assert c.post("/api/v1/admin/users", headers=H("admin"), json=body).status_code == 409  # duplicate address, same generic message

    assert c.post(f"/api/v1/admin/users/{ADMIN}/deactivate", headers=H("admin")).status_code == 400  # not yourself
    d = c.post(f"/api/v1/admin/users/{new_id}/deactivate", headers=H("admin"))
    assert d.status_code == 200 and auth.banned[new_id] is True and repo.profiles[new_id]["deactivated_at"]
    assert c.get("/api/v1/admin/users?status=deactivated", headers=H("admin")).json()["total"] == 1
    assert c.post(f"/api/v1/admin/users/{new_id}/reactivate", headers=H("admin")).status_code == 200
    assert auth.banned[new_id] is False and repo.profiles[new_id]["deactivated_at"] is None
    events = {a["event_type"] for a in repo.audit}
    assert {"admin.user_created", "admin.user_deactivated", "admin.user_reactivated"} <= events
    assert all("email" not in str(a["metadata"]) for a in repo.audit)  # no addresses in the audit log
    assert c.post("/api/v1/admin/users/00000000-0000-4000-8000-0000000000ff/deactivate", headers=H("admin")).status_code == 404


def test_overview_queue_metrics_and_dead_letter_requeue(admin_env):
    c, repo, _ = admin_env
    seed(repo)
    t0 = datetime.now(UTC) - timedelta(minutes=5)
    iso = lambda dt: dt.isoformat()  # noqa: E731
    repo.submissions += [
        {"id": "s-ok", "learner_id": L1, "exercise_id": EX, "status": "passed", "created_at": iso(t0), "started_at": iso(t0 + timedelta(seconds=4)),
         "finished_at": iso(t0 + timedelta(seconds=6)), "claim_count": 1},
        {"id": "00000000-0000-4000-8000-0000000000d1", "learner_id": L2, "exercise_id": EX, "status": "error", "created_at": iso(t0),
         "started_at": iso(t0), "finished_at": iso(t0 + timedelta(seconds=200)), "claim_count": 3},
        {"id": "00000000-0000-4000-8000-0000000000d2", "learner_id": L2, "exercise_id": EX, "status": "failed", "created_at": iso(t0), "claim_count": 1}]
    q = c.get("/api/v1/admin/queue", headers=H("admin")).json()
    assert [d["submission_id"] for d in q["dead_letters"]] == ["00000000-0000-4000-8000-0000000000d1"]
    wait = q["grading_24h"]["queue_wait_seconds"]
    assert wait["p50"] in (0.0, 4.0) and wait["max"] == 4.0 and q["grading_24h"]["execution_seconds"]["max"] == 200.0
    ov = c.get("/api/v1/admin/overview", headers=H("admin")).json()
    assert ov["users"] == {"learners": 2, "teachers": 2, "admins": 1, "deactivated": 0} and ov["dead_letters"] == 1 and ov["health"]["database"] is True
    # only a dead-lettered system error can be requeued; a learner's own failed attempt cannot
    assert c.post("/api/v1/admin/submissions/00000000-0000-4000-8000-0000000000d2/requeue", headers=H("admin")).status_code == 404
    r = c.post("/api/v1/admin/submissions/00000000-0000-4000-8000-0000000000d1/requeue", headers=H("admin"))
    assert r.status_code == 200
    s = next(x for x in repo.submissions if x["id"].endswith("d1"))
    assert s["status"] == "queued" and s["claim_count"] == 0 and s["claimed_by"] is None
    assert c.post("/api/v1/admin/submissions/00000000-0000-4000-8000-0000000000d1/requeue", headers=H("admin")).status_code == 404  # not twice
    assert any(a["event_type"] == "admin.submission_requeued" for a in repo.audit)


def test_audit_viewer_filters_and_pages(admin_env):
    c, repo, _ = admin_env
    seed(repo)
    for i in range(5):
        repo.audit.append({"id": f"a{i}", "actor_id": L1, "event_type": "lecture.opened" if i % 2 else "auth.denied", "resource_type": "x",
                           "resource_id": None, "request_id": None, "metadata": {}, "created_at": f"2026-01-0{i + 1}"})
    r = c.get("/api/v1/admin/audit?limit=2", headers=H("admin")).json()
    assert r["total"] >= 5 and len(r["events"]) == 2 and r["events"][0]["created_at"] >= r["events"][1]["created_at"]
    only = c.get("/api/v1/admin/audit?event_type=auth.denied&actor_id=" + L1, headers=H("admin")).json()
    assert only["total"] == 3 and all(e["event_type"] == "auth.denied" for e in only["events"])
    assert c.get("/api/v1/admin/audit?limit=500", headers=H("admin")).status_code == 422


def test_course_overview_and_lecture_status(admin_env):
    c, repo, _ = admin_env
    seed(repo)
    r = c.get("/api/v1/admin/courses", headers=H("admin")).json()["courses"][0]
    assert r["learners_enrolled"] == 2 and r["lectures"][0]["exercises"][0]["test_suite_version"] == 1
    assert c.patch(f"/api/v1/admin/lectures/{LID}/status", headers=H("teacher"), json={"status": "draft"}).status_code == 403
    assert c.patch(f"/api/v1/admin/lectures/{LID}/status", headers=H("admin"), json={"status": "bogus"}).status_code == 422
    ok = c.patch(f"/api/v1/admin/lectures/{LID}/status", headers=H("admin"), json={"status": "archived"})
    assert ok.status_code == 200 and ok.json()["previous_status"] == "published" and repo.d["lecture"]["status"] == "archived"
    repo.d["segments"].clear()
    assert c.patch(f"/api/v1/admin/lectures/{LID}/status", headers=H("admin"), json={"status": "published"}).status_code == 422


def test_cohorts_sync_enrolment_and_teacher_assignment(admin_env):
    c, repo, _ = admin_env
    seed(repo)
    repo.enrollments.pop(L2, None)
    r = c.post("/api/v1/admin/cohorts", headers=H("admin"), json={"course_id": CID, "name": "Autumn A"})
    assert r.status_code == 201
    cid = r.json()["id"]
    assert c.post("/api/v1/admin/cohorts", headers=H("admin"), json={"course_id": CID, "name": "Autumn A"}).status_code == 409
    assert c.put(f"/api/v1/admin/cohorts/{cid}/teachers/{L1}", headers=H("admin")).status_code == 404  # a learner cannot teach
    assert c.put(f"/api/v1/admin/cohorts/{cid}/members/{T1}", headers=H("admin")).status_code == 404
    assert c.put(f"/api/v1/admin/cohorts/{cid}/members/{L1}", headers=H("admin")).status_code == 204
    assert c.put(f"/api/v1/admin/cohorts/{cid}/teachers/{T1}", headers=H("admin")).status_code == 204  # assigns existing members
    assert c.put(f"/api/v1/admin/cohorts/{cid}/members/{L2}", headers=H("admin")).status_code == 204  # enrols and assigns the new member
    assert set(repo.assignments[T1]) == {L1, L2} and CID in repo.enrollments[L2]
    assert c.get(f"/api/v1/teacher/learners/{L2}/results", headers=H("teacher")).status_code == 200
    shown = c.get("/api/v1/admin/cohorts", headers=H("admin")).json()["cohorts"][0]
    assert {x["display_name"] for x in shown["learners"]} == {"Asha", "Bilal"} and [t["display_name"] for t in shown["teachers"]] == ["Tara"]
    # removing a member revokes the teacher's access unless another shared cohort still grants it
    assert c.delete(f"/api/v1/admin/cohorts/{cid}/members/{L2}", headers=H("admin")).status_code == 204
    assert c.get(f"/api/v1/teacher/learners/{L2}/results", headers=H("teacher")).status_code == 404
    assert c.delete(f"/api/v1/admin/cohorts/{cid}/teachers/{T1}", headers=H("admin")).status_code == 204
    assert repo.assignments[T1] == []
    assert c.delete(f"/api/v1/admin/cohorts/{cid}", headers=H("admin")).status_code == 204
    assert c.get("/api/v1/admin/cohorts", headers=H("admin")).json()["cohorts"] == []
    assert c.put(f"/api/v1/admin/cohorts/{cid}/members/{L1}", headers=H("admin")).status_code == 404  # archived


def test_issue_queue_workflow_and_settings(admin_env):
    c, repo, _ = admin_env
    seed(repo)
    made = c.post("/api/v1/me/issues", headers=H("learner1"), json={"category": "content", "message": "Typo in lesson 2", "page": "/lectures/x"})
    assert made.status_code == 201
    iid = made.json()["id"]
    listing = c.get("/api/v1/admin/issues", headers=H("admin")).json()
    assert listing["total"] == 1 and listing["issues"][0]["reporter"] == "Asha" and listing["issues"][0]["reference"] == iid[:8].upper()
    assert c.patch(f"/api/v1/admin/issues/{iid}", headers=H("learner1"), json={"status": "resolved"}).status_code == 403
    r = c.patch(f"/api/v1/admin/issues/{iid}", headers=H("admin"), json={"status": "resolved", "admin_note": "Fixed in v3"})
    assert r.status_code == 200
    assert c.get("/api/v1/admin/issues", headers=H("admin")).json()["total"] == 0
    assert c.get("/api/v1/admin/issues?status=resolved", headers=H("admin")).json()["issues"][0]["admin_note"] == "Fixed in v3"
    s = c.get("/api/v1/admin/settings", headers=H("admin")).json()
    assert s["read_only"] is True and any(i["label"].startswith("Worker lease") for i in s["settings"])
    assert not any(i["value"].startswith(("eyJ", "sb_")) or "secret" in i["label"].lower() for i in s["settings"])  # no secrets
