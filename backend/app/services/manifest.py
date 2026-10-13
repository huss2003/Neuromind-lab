"""Builds the learner-safe lecture manifest. Never includes answer keys or tests."""
from typing import Any

from pydantic import BaseModel


class NextAction(BaseModel):
    type: str
    exercise_id: str | None = None


class Media(BaseModel):
    provider: str | None
    url: str | None
    captions_url: str | None = None
    transcript: str | None = None


class QuestionOut(BaseModel):
    id: str
    prompt: str
    options: list[dict[str, str]]


class CheckpointOut(BaseModel):
    id: str
    type: str
    required: bool
    question: QuestionOut


class SegmentOut(BaseModel):
    id: str
    order: int
    type: str
    title: str
    required: bool
    media: Media | None = None
    checkpoint: CheckpointOut | None = None
    exercise_id: str | None = None
    next_action: NextAction


class LectureManifest(BaseModel):
    id: str
    lecture_number: int
    title: str
    summary: str
    learning_objectives: list[str]
    duration_seconds: int | None
    content_version: int
    segments: list[SegmentOut]


class ManifestError(Exception):
    """Content configuration error (never silently treated as completion)."""


def build_segment(seg: dict[str, Any], checkpoint: dict[str, Any] | None) -> SegmentOut:
    stype = seg["segment_type"]
    next_action = NextAction(type="next_segment")
    on_end = (seg.get("settings") or {}).get("on_end")
    if on_end and on_end.get("type") == "open_exercise":
        if not on_end.get("exercise_id"):
            raise ManifestError(f"segment {seg['id']}: open_exercise without exercise_id")
        next_action = NextAction(type="open_exercise", exercise_id=on_end["exercise_id"])
    out = SegmentOut(
        id=seg["id"], order=seg["segment_order"], type=stype, title=seg["title"],
        required=seg["is_required"], next_action=next_action,
    )
    if stype == "video":
        cfg = seg.get("settings") or {}
        out.media = Media(provider=seg.get("media_provider"), url=seg.get("media_url"),
                          captions_url=cfg.get("captions_url"), transcript=cfg.get("transcript"))
    elif stype in ("checkpoint", "exit_check"):
        if not checkpoint or not checkpoint.get("question"):
            raise ManifestError(f"segment {seg['id']}: checkpoint or question missing")
        q = checkpoint["question"]
        out.checkpoint = CheckpointOut(
            id=checkpoint["id"], type=checkpoint["checkpoint_type"], required=checkpoint["required"],
            question=QuestionOut(id=q["id"], prompt=q["prompt"], options=q["options"]),
        )
    elif stype == "exercise":
        if not seg.get("exercise_id"):
            raise ManifestError(f"segment {seg['id']}: exercise missing")
        out.exercise_id = seg["exercise_id"]
    return out
