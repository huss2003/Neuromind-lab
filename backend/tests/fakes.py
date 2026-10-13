"""In-memory Repository + helpers for API tests (no network)."""
import copy
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException

from app.auth import CurrentUser
from app.grader_client import GradeResult

LID = "00000000-0000-4000-8000-000000000009"
CID = "00000000-0000-4000-8000-000000000001"
CP1, CP2, CP3 = (f"00000000-0000-4000-8000-0000000000c{i}" for i in (1, 2, 3))
Q1, Q2, Q3 = (f"00000000-0000-4000-8000-0000000000a{i}" for i in (1, 2, 3))
EX = "00000000-0000-4000-8000-0000000000e1"
SEG = {i: f"00000000-0000-4000-8000-00000000010{i}" for i in range(1, 8)}


def now() -> str:
    return datetime.now(UTC).isoformat()


def build_data() -> dict[str, Any]:
    def seg(n, t, **kw):
        return {"id": SEG[n], "lecture_id": LID, "segment_order": n, "segment_type": t, "title": f"S{n}",
                "is_required": True, "settings": {}, "media_provider": None, "media_url": None,
                "checkpoint_id": None, "exercise_id": None, **kw}

    opts = [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}, {"id": "c", "text": "C"}]

    def q(i, correct):
        return {"id": i, "prompt": f"Q {i[-2:]}", "options": opts, "correct_option_id": correct, "points": 1,
                "explanation_correct": "Right because X", "explanation_incorrect": "Wrong; see X"}

    return {
        "course": {"id": CID, "slug": "c", "title": "C", "description": "", "status": "published"},
        "module": {"id": "m", "module_number": 1, "title": "Module 1", "description": "", "sort_order": 1},
        "lecture": {"id": LID, "course_id": CID, "module_id": "m", "lecture_number": 9, "title": "L9", "summary": "",
                    "learning_objectives": [], "duration_seconds": 3600, "content_version": 1, "status": "published"},
        "segments": [
            seg(1, "video", media_url="http://x/1.mp4"),
            seg(2, "checkpoint", checkpoint_id=CP1),
            seg(3, "video", media_url="http://x/3.mp4"),
            seg(4, "checkpoint", checkpoint_id=CP2),
            seg(5, "video", media_url="http://x/5.mp4", settings={"on_end": {"type": "open_exercise", "exercise_id": EX}}),
            seg(6, "exercise", exercise_id=EX),
            seg(7, "exit_check", checkpoint_id=CP3),
        ],
        "checkpoints": {
            CP1: {"id": CP1, "lecture_id": LID, "checkpoint_type": "mcq", "required": True, "pass_threshold": None, "question_id": Q1},
            CP2: {"id": CP2, "lecture_id": LID, "checkpoint_type": "mcq", "required": True, "pass_threshold": None, "question_id": Q2},
            CP3: {"id": CP3, "lecture_id": LID, "checkpoint_type": "exit_check", "required": True, "pass_threshold": 100, "question_id": Q3},
        },
        "questions": {Q1: q(Q1, "b"), Q2: q(Q2, "a"), Q3: q(Q3, "c")},
        "exercise": {"id": EX, "lecture_id": LID, "title": "Print", "instructions": "Do it", "language": "python",
                     "starter_code": "x=1", "practice_mode": "both", "pass_threshold": 80, "max_attempts": None, "status": "published",
                     "test_suite_version": 1, "hints": ["hint one", "hint two", "hint three"], "hint_penalty_percent": 10},
        "tests": [
            {"id": "t1", "exercise_id": EX, "test_order": 1, "test_type": "stdout", "definition": {"secret": "HIDDEN-EXPECTED"},
             "points": 1, "is_hidden": True, "criterion_label": "SECRET-LABEL", "remediation": "Review how print works."},
            {"id": "t2", "exercise_id": EX, "test_order": 2, "test_type": "stdout", "definition": {"description": "visible"},
             "points": 1, "is_hidden": False, "criterion_label": "Prints a value", "remediation": "Add a print call."},
        ],
    }


class InMemoryRepository:
    def __init__(self) -> None:
        self.d = build_data()
        self.sessions: dict[str, dict] = {}
        self.attempts: list[dict] = []
        self.submissions: list[dict] = []
        self.profiles: dict[str, dict] = {}
        self.progress: dict[tuple, dict] = {}
        self.audit: list[dict] = []
        self.reveals: list[dict] = []
        self.drafts: dict[tuple, str] = {}
        self.assignments: dict[str, list[str]] = {}
        self.feedback: list[dict] = []

    # content
    async def list_published_courses(self): return [self.d["course"]]
    async def get_published_course(self, i): return self.d["course"] if i == CID else None
    async def list_published_lectures(self, c): return [self.d["lecture"]]
    async def get_published_lecture(self, i): return copy.deepcopy(self.d["lecture"]) if i == LID else None
    async def list_segments(self, lecture_id): return copy.deepcopy(self.d["segments"]) if lecture_id == LID else []

    async def get_checkpoint_with_question(self, cid):
        cp = self.d["checkpoints"].get(cid)
        if not cp:
            return None
        q = self.d["questions"][cp["question_id"]]
        return {**cp, "question": {"id": q["id"], "prompt": q["prompt"], "options": q["options"]}}

    async def get_checkpoint(self, cid): return copy.deepcopy(self.d["checkpoints"].get(cid))
    async def get_question_full(self, qid): return copy.deepcopy(self.d["questions"].get(qid))
    async def get_published_exercise(self, eid): return copy.deepcopy(self.d["exercise"]) if eid == EX else None
    async def list_exercise_tests(self, eid): return copy.deepcopy(self.d["tests"])

    # state
    async def get_session(self, learner, lecture):
        return copy.deepcopy(next((s for s in self.sessions.values() if s["learner_id"] == learner and s["lecture_id"] == lecture), None))

    async def create_session(self, learner, lecture, first):
        s = {"id": str(uuid.uuid4()), "learner_id": learner, "lecture_id": lecture, "current_segment_id": first,
             "playback_position_seconds": 0, "status": "in_progress", "state_version": 1, "last_seen_at": now(),
             "completed_at": None}
        self.sessions[s["id"]] = s
        return copy.deepcopy(s)

    async def update_session(self, sid, expected, fields):
        s = self.sessions[sid]
        if expected is not None:
            if s["state_version"] != expected:
                return None
            fields = {**fields, "state_version": expected + 1}
        s.update(fields)
        return copy.deepcopy(s)

    async def list_attempts(self, learner, cps):
        return copy.deepcopy([a for a in self.attempts if a["learner_id"] == learner and a["checkpoint_id"] in cps])

    async def find_attempt_by_key(self, learner, key):
        return copy.deepcopy(next((a for a in self.attempts if a["learner_id"] == learner and a["idempotency_key"] == key), None))

    async def insert_attempt(self, row):
        r = {**row, "id": str(uuid.uuid4()), "submitted_at": now()}
        self.attempts.append(r)
        return copy.deepcopy(r)

    async def list_submissions(self, learner, eids):
        return copy.deepcopy([s for s in self.submissions if s["learner_id"] == learner and s["exercise_id"] in eids])

    async def get_submission(self, sid): return copy.deepcopy(next((s for s in self.submissions if s["id"] == sid), None))

    async def find_submission_by_key(self, learner, key):
        return copy.deepcopy(next((s for s in self.submissions if s["learner_id"] == learner and s["idempotency_key"] == key), None))

    async def insert_submission(self, row):
        n = 1 + len([s for s in self.submissions if s["learner_id"] == row["learner_id"] and s["exercise_id"] == row["exercise_id"]])
        r = {"score": None, "raw_score": None, "passed_tests": 0, "total_tests": 0, "safe_feedback": [],
             "execution_ms": None, "created_at": now(), "criteria_results": [], "hints_used": 0, "hint_penalty": 0,
             "max_score": 100, **row, "id": str(uuid.uuid4()), "submission_number": n}
        self.submissions.append(r)
        return copy.deepcopy(r)

    async def update_submission(self, sid, fields):
        s = next((s for s in self.submissions if s["id"] == sid), None)
        if s:
            s.update(fields)
        return copy.deepcopy(s)

    async def recompute_progress(self, learner, course):
        done = len([s for s in self.sessions.values() if s["learner_id"] == learner and s["status"] == "completed"])
        row = {"learner_id": learner, "course_id": course, "completed_lectures": done, "total_lectures": 1}
        self.progress[(learner, course)] = row
        return row

    async def list_published_modules(self, course_id): return [self.d["module"]]
    async def insert_audit(self, row): self.audit.append(row)

    async def list_hint_reveals(self, learner, exercise, number):
        return sorted([r for r in self.reveals if r["learner_id"] == learner and r["exercise_id"] == exercise
                       and r["attempt_number"] == number], key=lambda r: r["hint_index"])

    async def insert_hint_reveal(self, row):
        self.reveals.append(dict(row))
        return dict(row)

    async def get_draft(self, learner, exercise):
        code = self.drafts.get((learner, exercise))
        return {"source_code": code} if code is not None else None

    async def upsert_draft(self, learner, exercise, code): self.drafts[(learner, exercise)] = code

    async def submission_load(self, learner, since_iso):
        mine = [s for s in self.submissions if s["learner_id"] == learner]
        return len([s for s in mine if s["created_at"] >= since_iso]), len([s for s in mine if s["status"] in ("queued", "running")])

    async def list_assigned_learner_ids(self, teacher): return list(self.assignments.get(teacher, []))

    async def list_learners_page(self, ids, q, limit, offset):
        rows = [p for p in self.profiles.values() if p["role"] == "learner" and (ids is None or p["id"] in ids)]
        if q:
            rows = [p for p in rows if q.lower() in p["display_name"].lower()]
        rows.sort(key=lambda p: p["display_name"])
        return rows[offset:offset + limit], len(rows)

    async def titles(self, lecture_ids, checkpoint_ids, exercise_ids):
        return {"lectures": {i: "Lecture 9: L9" for i in lecture_ids},
                "checkpoints": {i: f"Check {i[-2:]}" for i in checkpoint_ids}, "exercises": {i: "Print" for i in exercise_ids}}

    async def insert_feedback(self, row):
        r = {**row, "id": str(uuid.uuid4()), "created_at": now()}
        self.feedback.append(r)
        return dict(r)

    async def list_feedback(self, learner, published_only):
        return [dict(f) for f in self.feedback if f["learner_id"] == learner and (f["published"] or not published_only)]

    async def ping(self): return True

    async def list_learners(self): return [p for p in self.profiles.values() if p["role"] == "learner"]
    async def get_profile(self, uid): return self.profiles.get(uid)
    async def list_learner_sessions(self, learner): return [s for s in self.sessions.values() if s["learner_id"] == learner]
    async def list_learner_attempts(self, learner): return [a for a in self.attempts if a["learner_id"] == learner]
    async def list_learner_submissions(self, learner): return [s for s in self.submissions if s["learner_id"] == learner]


class FakeVerifier:
    users = {
        "learner1": CurrentUser("11111111-1111-4111-8111-111111111111", "learner", "l1@x.test", "Learner One"),
        "learner2": CurrentUser("22222222-2222-4222-8222-222222222222", "learner", "l2@x.test", "Learner Two"),
        "teacher": CurrentUser("33333333-3333-4333-8333-333333333333", "teacher", "t@x.test", "Teacher"),
        "teacher2": CurrentUser("44444444-4444-4444-8444-444444444444", "teacher", "t2@x.test", "Teacher Two"),
        "admin": CurrentUser("55555555-5555-4555-8555-555555555555", "admin", "a@x.test", "Admin"),
    }

    async def verify(self, token):
        if token not in self.users:
            raise HTTPException(401)
        return self.users[token]


class FakeGrader:
    """Grades by looking for a marker in the code; records what it was given."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.down = False

    async def grade(self, source_code, tests, pass_threshold):
        self.calls.append((source_code, tests))
        if self.down:
            return GradeResult("error", feedback=[{"kind": "infrastructure", "message": "grader unavailable"}])
        if "GOOD" in source_code:
            return GradeResult("passed", 2, 2, 100.0, 10, [{"kind": "success", "message": "All required tests passed."}],
                               [{"test_order": 1, "passed": True}, {"test_order": 2, "passed": True}], "test-1.0")
        if "HALF" in source_code:
            return GradeResult("failed", 1, 2, 50.0, 10, [{"kind": "failure", "message": "Some checks failed."}],
                               [{"test_order": 1, "passed": False}, {"test_order": 2, "passed": True}], "test-1.0")
        return GradeResult("failed", 0, 2, 0.0, 10, [{"kind": "failure", "message": "Test 1 failed."}],
                           [{"test_order": 1, "passed": False}, {"test_order": 2, "passed": False}], "test-1.0")
