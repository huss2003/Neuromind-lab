"""Assessment policy (pure functions). Requirements v1.0 §6.2:
- every attempt is stored; the best valid score is the highest score among completed graded attempts;
- hint use lowers the CURRENT attempt's score by `hint_penalty_percent` points per hint (floor 0) and never the
  learner's earlier best score. The exact formula is an open product decision (§25); this is the documented default."""
from typing import Any

Row = dict[str, Any]
VALID_STATUSES = ("passed", "failed")  # completed, graded attempts (not timeout/error/infrastructure)


def apply_hint_penalty(raw_score: float, hints_used: int, penalty_percent: float) -> tuple[float, float]:
    penalty = min(float(raw_score), hints_used * float(penalty_percent))
    return round(float(raw_score) - penalty, 2), round(penalty, 2)


def decide_status(grader_status: str, adjusted_score: float | None, threshold: float) -> str:
    """Pass/fail is recomputed from the adjusted score; timeouts/infrastructure errors are never converted."""
    if grader_status in ("passed", "failed"):
        return "passed" if adjusted_score is not None and adjusted_score >= threshold else "failed"
    return grader_status


def best_valid_score(submissions: list[Row]) -> float | None:
    scores = [float(s["score"]) for s in submissions if s["status"] in VALID_STATUSES and s.get("score") is not None]
    return max(scores) if scores else None


def build_criteria(tests: list[Row], grader_criteria: list[Row]) -> list[Row]:
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
        out.append({"label": label, "hidden": bool(t["is_hidden"]), "passed": passed,
                    "remediation": None if passed else t.get("remediation")})
    return out
