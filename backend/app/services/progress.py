"""Server-authoritative lecture progress rules (pure functions, no I/O).

Gate = a required segment the learner must complete before later segments become reachable:
  - checkpoint / exit_check: completed once an attempt meets the checkpoint's threshold
    (no threshold => any submitted attempt completes it)
  - exercise: completed once a submission has status `passed`
Video segments are never gates (watching cannot be verified server-side).
"""
from dataclasses import dataclass, field
from typing import Any

Row = dict[str, Any]
GATE_TYPES = ("checkpoint", "exit_check", "exercise")


def attempt_meets_threshold(attempt: Row, checkpoint: Row, points: float) -> bool:
    threshold = checkpoint.get("pass_threshold")
    if threshold is None:
        return True
    pct = 100 * float(attempt["score"]) / points if points else 0
    return pct >= float(threshold)


@dataclass
class Progress:
    completed_checkpoint_ids: set[str] = field(default_factory=set)
    completed_exercise_ids: set[str] = field(default_factory=set)


def is_gate(segment: Row, checkpoints: dict[str, Row]) -> bool:
    if not segment["is_required"] or segment["segment_type"] not in GATE_TYPES:
        return False
    if segment["segment_type"] == "exercise":
        return True
    cp = checkpoints.get(segment.get("checkpoint_id") or "")
    return bool(cp and cp.get("required", True))


def segment_completed(segment: Row, progress: Progress) -> bool:
    if segment["segment_type"] == "exercise":
        return segment.get("exercise_id") in progress.completed_exercise_ids
    return segment.get("checkpoint_id") in progress.completed_checkpoint_ids


def missing_gates(segments: list[Row], checkpoints: dict[str, Row], progress: Progress) -> list[Row]:
    ordered = sorted(segments, key=lambda s: s["segment_order"])
    return [s for s in ordered if is_gate(s, checkpoints) and not segment_completed(s, progress)]


def max_reachable_order(segments: list[Row], checkpoints: dict[str, Row], progress: Progress) -> int:
    """Highest segment_order the learner may be at: the first incomplete gate (inclusive)."""
    gaps = missing_gates(segments, checkpoints, progress)
    if gaps:
        return gaps[0]["segment_order"]
    return max((s["segment_order"] for s in segments), default=0)
