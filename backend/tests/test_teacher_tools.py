from tests.conftest import H
from tests.fakes import CID

L1 = "11111111-1111-4111-8111-111111111111"
L2 = "22222222-2222-4222-8222-222222222222"
T1 = "33333333-3333-4333-8333-333333333333"
T2 = "44444444-4444-4444-8444-444444444444"


def setup(repo, l1_name="Asha"):
    repo.profiles.update({L1: {"id": L1, "display_name": l1_name, "role": "learner"}, L2: {"id": L2, "display_name": "Bilal", "role": "learner"},
                          T1: {"id": T1, "display_name": "Tara", "role": "teacher"}, T2: {"id": T2, "display_name": "Tomas", "role": "teacher"}})
    repo.assignments[T1] = [L1]
    repo.assignments[T2] = [L2]


def test_progress_report_is_limited_to_the_teachers_own_learners(env):
    c, repo, _ = env
    setup(repo)
    r = c.get("/api/v1/teacher/reports/progress", headers=H("teacher")).json()["rows"]
    assert [x["learner"] for x in r] == ["Asha"]
    assert [x["learner"] for x in c.get("/api/v1/teacher/reports/progress", headers=H("teacher2")).json()["rows"]] == ["Bilal"]
    assert {x["learner"] for x in c.get("/api/v1/teacher/reports/progress", headers=H("admin")).json()["rows"]} == {"Asha", "Bilal"}
    assert c.get("/api/v1/teacher/reports/progress", headers=H("learner1")).status_code == 403
    assert any(a["event_type"] == "teacher.report_exported" for a in repo.audit)


def test_csv_export_neutralises_spreadsheet_formulas(env):
    c, repo, _ = env
    setup(repo, l1_name='=HYPERLINK("http://evil.example","x")')
    r = c.get("/api/v1/teacher/reports/progress?format=csv", headers=H("teacher"))
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv") and "attachment" in r.headers["content-disposition"]
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("learner,lectures_completed") and len(lines) == 2
    assert lines[1].startswith("\"'=HYPERLINK") or lines[1].startswith("'=HYPERLINK")  # defanged, not a live formula


def test_cohort_overview_and_report_by_cohort_respect_teacher_membership(admin_env):
    c, repo, _ = admin_env
    setup(repo)
    repo.assignments.clear()
    a = c.post("/api/v1/admin/cohorts", headers=H("admin"), json={"course_id": CID, "name": "A"}).json()["id"]
    b = c.post("/api/v1/admin/cohorts", headers=H("admin"), json={"course_id": CID, "name": "B"}).json()["id"]
    c.put(f"/api/v1/admin/cohorts/{a}/teachers/{T1}", headers=H("admin"))
    c.put(f"/api/v1/admin/cohorts/{a}/members/{L1}", headers=H("admin"))
    c.put(f"/api/v1/admin/cohorts/{b}/teachers/{T2}", headers=H("admin"))
    c.put(f"/api/v1/admin/cohorts/{b}/members/{L2}", headers=H("admin"))
    mine = c.get("/api/v1/teacher/cohorts", headers=H("teacher")).json()["cohorts"]
    assert [x["name"] for x in mine] == ["A"] and mine[0]["learners"] == 1
    assert {x["name"] for x in c.get("/api/v1/teacher/cohorts", headers=H("admin")).json()["cohorts"]} == {"A", "B"}
    assert [x["learner"] for x in c.get(f"/api/v1/teacher/reports/progress?cohort_id={a}", headers=H("teacher")).json()["rows"]] == ["Asha"]
    assert c.get(f"/api/v1/teacher/reports/progress?cohort_id={b}", headers=H("teacher")).status_code == 404  # another teacher's cohort
