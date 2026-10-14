"""Loads a learner's lecture context (segments, checkpoints, progress) from the repository."""
import asyncio
from dataclasses import dataclass
from typing import Any

from app.errors import ApiError
from app.repository import Repository
from app.services.progress import Progress, attempt_meets_threshold

Row = dict[str, Any]


@dataclass
class LectureContext:
    lecture: Row
    segments: list[Row]
    checkpoints: dict[str, Row]
    questions: dict[str, Row]
    attempts: list[Row]
    submissions: list[Row]
    progress: Progress
    exercises: dict[str, Row]


async def ensure_enrolled(repo: Repository, learner_id: str, course_id: str) -> None:
    """Unenrolled learners get the same 404 as a missing course (no existence leak)."""
    if course_id not in await repo.list_enrolled_course_ids(learner_id):
        raise ApiError(404, "NOT_FOUND")


async def ensure_available(repo: Repository, learner_id: str, lecture: Row) -> None:
    """Server-decided locking: every prerequisite lecture must be completed by this learner."""
    for pid in lecture.get("prerequisites") or []:
        prereq = await repo.get_session(learner_id, pid)
        if not prereq or prereq["status"] != "completed":
            raise ApiError(400, "LECTURE_LOCKED", "Complete the earlier lecture first to unlock this one.")


async def _checkpoint_with_question(repo: Repository, cid: str) -> tuple[Row | None, Row | None]:
    cp = await repo.get_checkpoint(cid)
    q = await repo.get_question_full(cp["question_id"]) if cp else None
    return cp, q


async def load_context(repo: Repository, learner_id: str, lecture_id: str) -> LectureContext:
    """Independent reads run concurrently: a request makes about four sequential database round trips instead of fifteen."""
    lecture = await repo.get_published_lecture(lecture_id)
    if not lecture:
        raise ApiError(404, "NOT_FOUND")
    enrolled, available, seg_rows = await asyncio.gather(
        ensure_enrolled(repo, learner_id, lecture["course_id"]), ensure_available(repo, learner_id, lecture),
        repo.list_segments(lecture_id), return_exceptions=True)
    for outcome in (enrolled, available, seg_rows):  # deterministic precedence: not enrolled, then locked, then any other failure
        if isinstance(outcome, BaseException):
            raise outcome
    segments = sorted(seg_rows, key=lambda x: x["segment_order"])
    checkpoint_ids = list(dict.fromkeys(sg["checkpoint_id"] for sg in segments if sg.get("checkpoint_id")))
    exercise_ids = [sg["exercise_id"] for sg in segments if sg.get("exercise_id")]
    cp_rows, ex_rows, attempts, submissions = await asyncio.gather(
        asyncio.gather(*[_checkpoint_with_question(repo, cid) for cid in checkpoint_ids]),
        asyncio.gather(*[repo.get_published_exercise(eid) for eid in exercise_ids]),
        repo.list_attempts(learner_id, checkpoint_ids), repo.list_submissions(learner_id, exercise_ids))
    checkpoints: dict[str, Row] = {}
    questions: dict[str, Row] = {}
    for cid, (cp, q) in zip(checkpoint_ids, cp_rows, strict=True):
        if cp:
            checkpoints[cid] = cp
            if q:
                questions[cp["question_id"]] = q
    exercises: dict[str, Row] = {eid: ex for eid, ex in zip(exercise_ids, ex_rows, strict=True) if ex}
    progress = Progress()
    for a in attempts:
        cp = checkpoints.get(a["checkpoint_id"])
        q = questions.get(a["question_id"])
        if cp and q and attempt_meets_threshold(a, cp, float(q["points"])):
            progress.completed_checkpoint_ids.add(a["checkpoint_id"])
    progress.completed_exercise_ids = {s["exercise_id"] for s in submissions if s["status"] == "passed"}
    return LectureContext(lecture, segments, checkpoints, questions, attempts, submissions, progress, exercises)
