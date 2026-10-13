"""Builds the learner-safe lecture manifest. Never includes answer keys or tests."""
import hashlib
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
    body: str | None = None
    next_action: NextAction


class Prereq(BaseModel):
    id: str
    title: str


class LectureManifest(BaseModel):
    estimated_minutes: int | None = None
    prerequisites: list[Prereq] = []
    completion_criteria: list[str] = []
    attempt_policy: str = ""
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


TEXT_TYPES = ('intro', 'reading', 'example', 'reflection')


def stable_shuffle(options: list[dict[str, str]], seed: str) -> list[dict[str, str]]:
    """Per-learner but refresh-stable order; correctness is by option id so it never changes."""
    return sorted(options, key=lambda o: hashlib.sha256(f"{seed}:{o['id']}".encode()).hexdigest())


def build_segment(seg: dict[str, Any], checkpoint: dict[str, Any] | None, learner_id: str | None = None) -> SegmentOut:
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
    cfg = seg.get("settings") or {}
    has_media = bool(seg.get("media_url") or seg.get("media_asset_key"))
    if stype == "video" or (stype in TEXT_TYPES and has_media):
        out.media = Media(provider=seg.get("media_provider"), url=seg.get("media_url"),
                          captions_url=cfg.get("captions_url"), transcript=cfg.get("transcript"))
    if stype in TEXT_TYPES:
        out.body = cfg.get("body")
        if not has_media and not out.body:
            raise ManifestError(f"segment {seg['id']}: text section has no body")
    if stype in ("checkpoint", "exit_check"):
        if not checkpoint or not checkpoint.get("question"):
            raise ManifestError(f"segment {seg['id']}: checkpoint or question missing")
        q = checkpoint["question"]
        out.checkpoint = CheckpointOut(
            id=checkpoint["id"], type=checkpoint["checkpoint_type"], required=checkpoint["required"],
            question=QuestionOut(id=q["id"], prompt=q["prompt"],
                                 options=stable_shuffle(q["options"], f"{learner_id}:{q['id']}") if q.get("shuffle_options") and learner_id else q["options"]),
        )
    if stype == "exercise":
        if not seg.get("exercise_id"):
            raise ManifestError(f"segment {seg['id']}: exercise missing")
        out.exercise_id = seg["exercise_id"]
    return out
