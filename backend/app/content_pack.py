"""Content packs: one JSON file describes a whole lecture (lessons, checks, lab). Pure functions, no I/O.

A pack is validated against the Pydantic models below, then turned into database rows with deterministic ids so that
re-importing the same pack updates rows instead of duplicating them. Hidden test definitions are NOT part of a pack:
they are supplied separately (a git-ignored file) so answers never enter Git.
"""
from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

NAMESPACE = uuid.UUID("5a1d3e84-7b6c-4f1e-9a52-0c2d8e4b7f10")
SCHEMA_VERSION = 1
SEGMENT_TYPES = ("intro", "reading", "example", "checkpoint", "exercise", "exit_check")


class PackError(ValueError):
    """Raised when a pack cannot be turned into rows (missing private test definitions, unknown prerequisite)."""


def uid(name: str) -> str:
    return str(uuid.uuid5(NAMESPACE, name))


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Option(_Strict):
    id: str = Field(min_length=1, max_length=8)
    text: str = Field(min_length=1, max_length=300)


class Question(_Strict):
    prompt: str = Field(min_length=5, max_length=1000)
    options: list[Option] = Field(min_length=2, max_length=6)
    correct_option_id: str
    explanation_correct: str = Field(min_length=5, max_length=1500)
    explanation_incorrect: str = Field(min_length=5, max_length=1500)
    shuffle_options: bool = False

    @model_validator(mode="after")
    def _options_consistent(self) -> Question:
        ids = [o.id for o in self.options]
        if len(set(ids)) != len(ids):
            raise ValueError("option ids must be unique")
        if self.correct_option_id not in ids:
            raise ValueError(f"correct_option_id '{self.correct_option_id}' is not one of the option ids {ids}")
        if len({o.text.strip().lower() for o in self.options}) != len(self.options):
            raise ValueError("two options have the same text")
        return self


class Checkpoint(_Strict):
    key: str = Field(pattern=r"^[a-z0-9_-]{1,40}$")
    type: Literal["mcq", "exit_check"]
    question: Question
    pass_threshold: int | None = Field(default=None, ge=1, le=100)


class Example(_Strict):
    description: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=2000)
    expected_output: str = Field(max_length=1000)


class LabTest(_Strict):
    key: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,60}$", description="Key of the definition in the private tests file (or inline below)")
    label: str = Field(default="", max_length=200)
    remediation: str = Field(min_length=5, max_length=500)
    objective: str = Field(min_length=3, max_length=200)
    remediation_segment: str | None = Field(default=None, description="Key of the segment the learner is sent back to")
    hidden: bool = False
    definition: dict[str, Any] | None = Field(default=None, description="Visible checks may carry their definition in the pack")


PACKAGES = ("numpy", "pandas", "matplotlib", "scikit-learn", "pillow", "requests")


class Asset(_Strict):
    name: str = Field(pattern=r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,100}$")
    content: str = Field(max_length=400_000)
    encoding: Literal["text", "base64"] = "text"
    description: str = Field(default="", max_length=300)


class Limits(_Strict):
    memory_mb: int | None = Field(default=None, ge=64, le=1024)
    timeout_seconds: float | None = Field(default=None, ge=1, le=60)


class QuizQuestion(_Strict):
    prompt: str = Field(min_length=5, max_length=1000)
    options: list[Option] = Field(min_length=2, max_length=6)
    correct_option_id: str
    explanation: str = Field(min_length=5, max_length=1500)
    points: int = Field(default=1, ge=1, le=10)

    @model_validator(mode="after")
    def _ok(self) -> QuizQuestion:
        ids = [o.id for o in self.options]
        if len(set(ids)) != len(ids) or self.correct_option_id not in ids:
            raise ValueError("options must have unique ids and correct_option_id must be one of them")
        return self


class RubricItem(_Strict):
    criterion: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5, max_length=600)
    max_points: int = Field(default=1, ge=1, le=20)


class Lab(_Strict):
    kind: Literal["code", "quiz", "written", "upload"] = "code"
    scoring: Literal["score", "pass_fail"] = "pass_fail"
    title: str = Field(min_length=3, max_length=120)
    objective: str = Field(min_length=5, max_length=300)
    instructions: str = Field(min_length=10, max_length=6000)
    constraints: str = Field(default="", max_length=1000)
    starter_code: str = Field(default="", max_length=6000)
    hints: list[str] = Field(default_factory=list, max_length=5)
    hints_max: int = Field(default=3, ge=0, le=5)
    hint_penalty_percent: int = Field(default=0, ge=0, le=100)
    pass_threshold: int | None = Field(default=None, ge=1, le=100)
    practice_mode: Literal["pyodide", "server", "both"] = "both"
    packages: list[Literal["numpy", "pandas", "matplotlib", "scikit-learn", "pillow", "requests"]] = Field(default_factory=list)
    assets: list[Asset] = Field(default_factory=list, max_length=20)
    limits: Limits = Field(default_factory=Limits)
    visible_examples: list[Example] = Field(default_factory=list, max_length=5)
    success_criteria: list[str] = Field(min_length=1, max_length=8)
    tests: list[LabTest] = Field(default_factory=list, max_length=20)
    questions: list[QuizQuestion] = Field(default_factory=list, max_length=30)
    rubric: list[RubricItem] = Field(default_factory=list, max_length=10)
    checklist: list[str] = Field(default_factory=list, max_length=12)
    solution: str | None = Field(default=None, max_length=8000, description="Reference solution; verified in CI, never imported")

    @model_validator(mode="after")
    def _kind_ok(self) -> Lab:
        keys = [t.key for t in self.tests]
        if len(set(keys)) != len(keys):
            raise ValueError("lab test keys must be unique")
        if self.kind == "code":
            if len(self.tests) < 2:
                raise ValueError("a code lab needs at least two checks")
            if not any(t.hidden for t in self.tests):
                raise ValueError("at least one lab test must be hidden so the lab cannot be solved by reading the criteria")
            if not self.hints:
                raise ValueError("a code lab needs at least one hint")
            if not self.solution:
                raise ValueError("a code lab needs a reference solution (it is verified, never shown)")
            if self.questions or self.rubric or self.checklist:
                raise ValueError("a code lab has no questions, rubric or checklist")
        if self.kind == "quiz":
            if len(self.questions) < 3:
                raise ValueError("a quiz lab needs at least three questions")
            if self.tests or self.rubric or self.checklist:
                raise ValueError("a quiz lab has only questions")
        if self.kind in ("written", "upload"):
            if len(self.rubric) < 2:
                raise ValueError(f"a {self.kind} lab needs a rubric of at least two criteria for the teacher")
            if self.tests or self.questions:
                raise ValueError(f"a {self.kind} lab has no automatic checks")
            if self.kind == "upload" and len(self.checklist) < 2:
                raise ValueError("an upload lab needs a checklist of at least two items")
        names = [a.name for a in self.assets]
        if len(set(names)) != len(names):
            raise ValueError("asset names must be unique")
        if self.scoring == "score" and self.pass_threshold is None:
            raise ValueError("score-mode labs need a pass_threshold")
        return self

    @property
    def effective_threshold(self) -> int:
        return 100 if self.scoring == "pass_fail" else int(self.pass_threshold or 80)


class Segment(_Strict):
    key: str = Field(pattern=r"^[a-z0-9_-]{1,40}$")
    type: Literal["intro", "reading", "example", "checkpoint", "exercise", "exit_check"]
    title: str = Field(min_length=2, max_length=120)
    body: str | None = Field(default=None, max_length=12000)
    checkpoint: str | None = None
    opens_exercise: bool = False


class LecturePack(_Strict):
    schema_version: Literal[1, 2]
    lecture_number: int = Field(ge=1, le=104)
    title: str = Field(min_length=3, max_length=120)
    summary: str = Field(min_length=10, max_length=500)
    objectives: list[str] = Field(min_length=1, max_length=8)
    duration_minutes: int = Field(ge=5, le=180)
    prerequisites: list[int] = Field(default_factory=list, max_length=5)
    lab_only: bool = Field(default=False, description="True until the lecture's teaching content is uploaded: intro + lab only")
    checkpoints: list[Checkpoint] = Field(default_factory=list, max_length=12)
    lab: Lab
    segments: list[Segment] = Field(min_length=2, max_length=40)

    @model_validator(mode="after")
    def _cross_references(self) -> LecturePack:
        if self.lecture_number in self.prerequisites:
            raise ValueError("a lecture cannot be its own prerequisite")
        if any(p >= self.lecture_number for p in self.prerequisites):
            raise ValueError("prerequisites must be earlier lectures")
        cp_keys = [c.key for c in self.checkpoints]
        if len(set(cp_keys)) != len(cp_keys):
            raise ValueError("checkpoint keys must be unique")
        seg_keys = [s.key for s in self.segments]
        if len(set(seg_keys)) != len(seg_keys):
            raise ValueError("segment keys must be unique")
        used: list[str] = []
        for s in self.segments:
            if s.type in ("intro", "reading", "example"):
                if not s.body or len(s.body.strip()) < 20:
                    raise ValueError(f"segment '{s.key}' ({s.type}) needs a body of at least 20 characters")
            if s.type in ("checkpoint", "exit_check"):
                if s.checkpoint not in cp_keys:
                    raise ValueError(f"segment '{s.key}' refers to unknown checkpoint '{s.checkpoint}'")
                used.append(s.checkpoint)  # type: ignore[arg-type]
                want = "exit_check" if s.type == "exit_check" else "mcq"
                actual = next(c.type for c in self.checkpoints if c.key == s.checkpoint)
                if actual != want:
                    raise ValueError(f"segment '{s.key}' is a {s.type} but checkpoint '{s.checkpoint}' is type {actual}")
            elif s.checkpoint:
                raise ValueError(f"segment '{s.key}' ({s.type}) must not set a checkpoint")
            if s.opens_exercise and s.type != "example":
                raise ValueError(f"only example segments may set opens_exercise (segment '{s.key}')")
        if sorted(used) != sorted(cp_keys):
            raise ValueError("every checkpoint must be used by exactly one segment, in order, and none may be unused")
        if used != cp_keys:
            raise ValueError("checkpoints must be defined in the same order as their segments")
        if sum(1 for s in self.segments if s.type == "exercise") != 1:
            raise ValueError("a lecture needs exactly one exercise segment")
        if self.lab_only:
            if self.checkpoints or any(s.type in ("checkpoint", "exit_check") for s in self.segments):
                raise ValueError("a lab-only lecture has no checkpoints yet")
            if self.segments[-1].type != "exercise":
                raise ValueError("a lab-only lecture ends with the lab")
        else:
            if not self.checkpoints:
                raise ValueError("a full lecture needs at least one checkpoint")
            if self.segments[-1].type != "exit_check":
                raise ValueError("the last segment must be the exit check")
            if sum(1 for s in self.segments if s.type == "exit_check") != 1:
                raise ValueError("a lecture needs exactly one exit check")
        ex_i = next(i for i, s in enumerate(self.segments) if s.type == "exercise")
        for t in self.lab.tests:
            if t.remediation_segment is not None:
                if t.remediation_segment not in seg_keys:
                    raise ValueError(f"lab test '{t.key}' remediation_segment '{t.remediation_segment}' is not a segment")
                if seg_keys.index(t.remediation_segment) >= ex_i:
                    raise ValueError(f"lab test '{t.key}' must send the learner back to a segment before the lab")
        return self


def check_pack(data: Any) -> tuple[LecturePack | None, list[str]]:
    """Validate raw JSON. Returns (pack, []) or (None, human-readable problems)."""
    try:
        return LecturePack.model_validate(data), []
    except Exception as exc:  # pydantic.ValidationError, or a bad top-level type
        errors = getattr(exc, "errors", None)
        if callable(errors):
            return None, [f"{'.'.join(str(p) for p in e['loc']) or 'pack'}: {e['msg']}" for e in errors()]
        return None, [str(exc)]


def check_collection(packs: list[LecturePack]) -> list[str]:
    """Problems that only show up across several packs (duplicate numbers)."""
    seen: dict[int, int] = {}
    for p in packs:
        seen[p.lecture_number] = seen.get(p.lecture_number, 0) + 1
    return [f"lecture number {n} appears {c} times" for n, c in sorted(seen.items()) if c > 1]


def build_rows(pack: LecturePack, tests: dict[str, dict], *, course_id: str, module_id: str,
               prerequisite_ids: dict[int, str] | None = None, publish: bool = False,
               published_at: str = "2026-10-13T00:00:00Z", content_version: int = 1, lecture_id: str | None = None) -> dict[str, list[dict]]:
    """Deterministic table rows for one lecture, in dependency order. Ids come from the lecture number and positions.
    `lecture_id` keeps an existing lecture's id (prerequisite links from later lectures stay valid)."""
    n = pack.lecture_number
    prereq_ids = prerequisite_ids or {}
    prereqs = []
    for p in pack.prerequisites:
        pid = prereq_ids.get(p) or uid(f"lecture{p}")
        prereqs.append(pid)
    missing = [t.key for t in pack.lab.tests if t.key not in tests and t.definition is None]
    if missing:
        raise PackError(f"missing hidden test definitions for: {', '.join(missing)}")
    status = "published" if publish else "draft"
    lid, ex = lecture_id or uid(f"lecture{n}"), uid(f"l{n}-ex")
    seg_id = {s.key: uid(f"l{n}-seg{k}") for k, s in enumerate(pack.segments, start=1)}
    cp_index = {c.key: i for i, c in enumerate(pack.checkpoints, start=1)}

    lecture = {"id": lid, "course_id": course_id, "module_id": module_id, "lecture_number": n, "title": pack.title,
               "summary": pack.summary, "learning_objectives": pack.objectives, "duration_seconds": pack.duration_minutes * 60,
               "status": status, "content_version": content_version, "prerequisites": prereqs,
               "published_at": published_at if publish else None}
    questions, checkpoints = [], []
    for c in pack.checkpoints:
        i = cp_index[c.key]
        q = c.question
        questions.append({"id": uid(f"l{n}-q{i}"), "question_key": uid(f"l{n}-qk{i}"), "question_version": 1, "prompt": q.prompt,
                          "options": [o.model_dump() for o in q.options], "correct_option_id": q.correct_option_id,
                          "explanation_correct": q.explanation_correct, "explanation_incorrect": q.explanation_incorrect,
                          "points": 1, "status": status, "shuffle_options": q.shuffle_options, "reveal_policy": "always"})
        threshold = c.pass_threshold if c.pass_threshold is not None else (100 if c.type == "exit_check" else None)
        checkpoints.append({"id": uid(f"l{n}-cp{i}"), "lecture_id": lid, "checkpoint_order": i, "checkpoint_type": c.type,
                            "question_id": uid(f"l{n}-q{i}"), "required": True, "pass_threshold": threshold, "settings": {}})
    lab = pack.lab
    exercise = {"id": ex, "lecture_id": lid, "title": lab.title, "instructions": lab.instructions, "language": "python",
                "starter_code": lab.starter_code, "practice_mode": lab.practice_mode, "pass_threshold": lab.effective_threshold,
                "max_attempts": None, "status": status, "test_suite_version": 1, "hints": lab.hints,
                "hint_penalty_percent": lab.hint_penalty_percent, "objective": lab.objective, "constraints": lab.constraints,
                "visible_examples": [e.model_dump() for e in lab.visible_examples], "success_criteria": lab.success_criteria,
                "lab_kind": lab.kind, "scoring": lab.scoring, "packages": list(lab.packages), "assets": [a.model_dump() for a in lab.assets],
                "limits": {k: v for k, v in lab.limits.model_dump().items() if v is not None}, "rubric": [r.model_dump() for r in lab.rubric],
                "checklist": lab.checklist, "hints_max": lab.hints_max}
    lab_questions = [{"id": uid(f"l{n}-lq{i}"), "exercise_id": ex, "question_order": i, "prompt": q.prompt, "options": [o.model_dump() for o in q.options],
                      "correct_option_id": q.correct_option_id, "explanation": q.explanation, "points": q.points}
                     for i, q in enumerate(lab.questions, start=1)]
    segments = []
    for k, s in enumerate(pack.segments, start=1):
        settings: dict[str, Any] = {}
        if s.body is not None:
            settings["body"] = s.body
        if s.opens_exercise:
            settings["on_end"] = {"type": "open_exercise", "exercise_id": ex}
        segments.append({"id": seg_id[s.key], "lecture_id": lid, "segment_order": k, "segment_type": s.type, "title": s.title,
                         "is_required": True, "settings": settings,
                         "checkpoint_id": uid(f"l{n}-cp{cp_index[s.checkpoint]}") if s.checkpoint else None,
                         "exercise_id": ex if s.type == "exercise" else None})
    exercise_tests = []
    for i, t in enumerate(lab.tests, start=1):
        exercise_tests.append({"id": uid(f"l{n}-test{i}"), "exercise_id": ex, "test_order": i, "test_type": "stdout",
                               "definition": tests.get(t.key, t.definition), "points": 1, "is_hidden": t.hidden, "criterion_label": t.label or None,
                               "remediation": t.remediation, "objective": t.objective,
                               "remediation_segment_id": seg_id[t.remediation_segment] if t.remediation_segment else None})
    return {"lectures": [lecture], "mcq_questions": questions, "lecture_checkpoints": checkpoints,
            "lecture_exercises": [exercise], "lecture_segments": segments, "exercise_tests": exercise_tests, "lab_questions": lab_questions}


# Order in which tables must be written (parents first). Segments point at checkpoints and exercises.
WRITE_ORDER = ["lectures", "mcq_questions", "lecture_checkpoints", "lecture_exercises", "lecture_segments", "exercise_tests", "lab_questions"]
