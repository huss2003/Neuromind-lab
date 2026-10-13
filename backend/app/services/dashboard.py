"""Learner-scoped derived views: lecture availability states, remediation queue, recent attempts (§5, §10, §12)."""
from typing import Any

from app.repository import Repository

Row = dict[str, Any]
UNRESOLVED = ("failed", "runtime_error")


async def remediation_queue(repo: Repository, learner_id: str) -> list[Row]:
    """Exercises with at least one evaluated failure and no later/earlier pass: what to work on next."""
    subs = await repo.list_learner_submissions(learner_id)
    by_ex: dict[str, list[Row]] = {}
    for s in subs:
        by_ex.setdefault(s["exercise_id"], []).append(s)
    pending: list[tuple[str, Row]] = []
    for ex_id, rows in by_ex.items():
        if any(r["status"] == "passed" for r in rows):
            continue
        evaluated = [r for r in rows if r["status"] in UNRESOLVED]
        if evaluated:
            pending.append((ex_id, evaluated[-1]))
    if not pending:
        return []
    basics = {e["id"]: e for e in await repo.list_exercises_basic([p[0] for p in pending])}
    titles = await repo.titles([b["lecture_id"] for b in basics.values()], [], list(basics))
    out = []
    for ex_id, sub in pending:
        failed = [c for c in (sub.get("criteria_results") or []) if not c.get("passed")]
        b = basics.get(ex_id, {})
        out.append({
            "exercise_id": ex_id, "exercise": titles["exercises"].get(ex_id), "lecture_id": b.get("lecture_id"),
            "lecture": titles["lectures"].get(b.get("lecture_id", "")), "last_status": sub["status"],
            "objectives": sorted({c["objective"] for c in failed if c.get("objective")}),
            "steps": [{"criterion": c["label"], "text": c.get("remediation"), "objective": c.get("objective"),
                       "review_title": c.get("review_title")} for c in failed if c.get("remediation")],
        })
    return out


async def recent_attempts(repo: Repository, learner_id: str, limit: int = 5) -> list[Row]:
    subs = await repo.list_learner_submissions(learner_id)
    ids = sorted({s["exercise_id"] for s in subs})
    basics = {e["id"]: e for e in await repo.list_exercises_basic(ids)}
    titles = await repo.titles([b["lecture_id"] for b in basics.values()], [], ids)
    best: dict[str, float] = {}
    for s in subs:
        if s["status"] in ("passed", "failed", "runtime_error") and s.get("score") is not None:
            best[s["exercise_id"]] = max(best.get(s["exercise_id"], 0.0), float(s["score"]))
    latest = sorted(subs, key=lambda s: str(s["created_at"]), reverse=True)[:limit]
    return [{"submission_id": s["id"], "exercise_id": s["exercise_id"], "exercise": titles["exercises"].get(s["exercise_id"]),
             "lecture_id": basics.get(s["exercise_id"], {}).get("lecture_id"), "number": s["submission_number"],
             "status": s["status"], "score": float(s["score"]) if s["score"] is not None else None,
             "best_score": best.get(s["exercise_id"]), "created_at": s["created_at"]} for s in latest]


async def lecture_states(repo: Repository, learner_id: str, lectures: list[Row]) -> dict[str, str]:
    """locked | available | in_progress | completed | needs_attention — decided by the server, never the browser."""
    sessions = {s["lecture_id"]: s for s in await repo.list_learner_sessions(learner_id)}
    attention = {q["lecture_id"] for q in await remediation_queue(repo, learner_id)}
    out: dict[str, str] = {}
    for lec in lectures:
        prereqs = lec.get("prerequisites") or []
        s = sessions.get(lec["id"])
        if any(sessions.get(p, {}).get("status") != "completed" for p in prereqs):
            out[lec["id"]] = "locked"
        elif s and s["status"] == "completed":
            out[lec["id"]] = "completed"
        elif lec["id"] in attention:
            out[lec["id"]] = "needs_attention"
        elif s:
            out[lec["id"]] = "in_progress"
        else:
            out[lec["id"]] = "available"
    return out
