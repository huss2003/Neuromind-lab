"""Loads a learner's lecture context (segments, checkpoints, progress) from the repository."""
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


async def load_context(repo: Repository, learner_id: str, lecture_id: str) -> LectureContext:
    lecture = await repo.get_published_lecture(lecture_id)
    if not lecture:
        raise ApiError(404, "NOT_FOUND")
    segments = sorted(await repo.list_segments(lecture_id), key=lambda s: s["segment_order"])
    checkpoints: dict[str, Row] = {}
    questions: dict[str, Row] = {}
    for seg in segments:
        cid = seg.get("checkpoint_id")
        if cid and cid not in checkpoints:
            cp = await repo.get_checkpoint(cid)
            if cp:
                checkpoints[cid] = cp
                q = await repo.get_question_full(cp["question_id"])
                if q:
                    questions[cp["question_id"]] = q
    exercise_ids = [s["exercise_id"] for s in segments if s.get("exercise_id")]
    attempts = await repo.list_attempts(learner_id, list(checkpoints))
    submissions = await repo.list_submissions(learner_id, exercise_ids)
    progress = Progress()
    for a in attempts:
        cp = checkpoints.get(a["checkpoint_id"])
        q = questions.get(a["question_id"])
        if cp and q and attempt_meets_threshold(a, cp, float(q["points"])):
            progress.completed_checkpoint_ids.add(a["checkpoint_id"])
    progress.completed_exercise_ids = {s["exercise_id"] for s in submissions if s["status"] == "passed"}
    return LectureContext(lecture, segments, checkpoints, questions, attempts, submissions, progress)
