"""Assessment policy (pure functions). Requirements v1.0 §6.2:
- every attempt is stored; the best valid score is the highest score among completed graded attempts;
- hint use lowers the CURRENT attempt's score by `hint_penalty_percent` points per hint (floor 0) and never the
  learner's earlier best score. The exact formula is an open product decision (§25); this is the documented default."""
from typing import Any

Row = dict[str, Any]
VALID_STATUSES = ("passed", "failed", "runtime_error")  # evaluated attempts (never timeout/expired/error/cancelled)


def apply_hint_penalty(raw_score: float, hints_used: int, penalty_percent: float) -> tuple[float, float]:
    penalty = min(float(raw_score), hints_used * float(penalty_percent))
    return round(float(raw_score) - penalty, 2), round(penalty, 2)


def decide_status(grader_status: str, adjusted_score: float | None, threshold: float, runtime_error: bool = False) -> str:
    """Pass/fail is recomputed from the adjusted score; timeouts/infrastructure errors are never converted.
    A learner program that crashed is `runtime_error` (an evaluated learner failure, score 0)."""
    if grader_status == "failed" and runtime_error:
        return "runtime_error"
    if grader_status in ("passed", "failed"):
        return "passed" if adjusted_score is not None and adjusted_score >= threshold else "failed"
    return grader_status


def best_valid_score(submissions: list[Row]) -> float | None:
    scores = [float(s["score"]) for s in submissions if s["status"] in VALID_STATUSES and s.get("score") is not None]
    return max(scores) if scores else None


def explanation_for(question: Row, is_correct: bool) -> str:
    """Reveal policy (§11.1): `always` explains every answer; `after_correct` withholds the explanation until correct."""
    if is_correct:
        return question.get("explanation_correct", "")
    if question.get("reveal_policy") == "after_correct":
        return "Not quite. Review the lesson and try again."
    return question.get("explanation_incorrect") or question.get("explanation_correct", "")


def build_criteria(tests: list[Row], grader_criteria: list[Row], section_titles: dict[str, str] | None = None) -> list[Row]:
    """Learner-safe per-criterion results. Hidden tests show a generic label; remediation is shown only on failure."""
    outcome = {c["test_order"]: bool(c["passed"]) for c in grader_criteria}
    out: list[Row] = []
    hidden_n = 0
    for t in sorted(tests, key=lambda x: x["test_order"]):
        if t["test_order"] not in outcome:
            continue
        passed = outcome[t["test_order"]]
        if t["is_hidden"]:
            hidden_n += 1
            label = f"Hidden check {hidden_n}"
        else:
            label = t.get("criterion_label") or str(t["definition"].get("description", f"Check {t['test_order']}"))
        seg_id = t.get("remediation_segment_id")
        out.append({"label": label, "hidden": bool(t["is_hidden"]), "passed": passed,
                    "remediation": None if passed else t.get("remediation"),
                    "objective": None if passed else t.get("objective"),
                    "review_segment_id": None if passed else seg_id,
                    "review_title": None if passed or not seg_id else (section_titles or {}).get(seg_id)})
    return out
