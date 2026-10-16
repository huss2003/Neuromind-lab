"""Practical-lab rules (pure functions + small repository helpers). See docs/01-product/PRACTICAL_LABS_SPEC.md.

Hints: a code lab with pass/fail scoring counts bulb hints per *cycle* (hints_max, default 3); a Redo starts a new cycle.
Score-mode exercises keep the older per-attempt hints with a score penalty."""
from __future__ import annotations

import re
from typing import Any

from app.repository import Repository

Row = dict[str, Any]
KINDS = ("code", "quiz", "written", "upload")
REVIEWED_KINDS = ("written", "upload")
MAX_TEXT_CHARS = 8000
LINK_RE = re.compile(r"^https://[^\s<>\"']{3,500}$")


def is_pass_fail(ex: Row) -> bool:
    return (ex.get("scoring") or "score") == "pass_fail"


def hints_max(ex: Row) -> int:
    n = int(ex.get("hints_max") if ex.get("hints_max") is not None else 3)
    return min(n, len(ex.get("hints") or []))


async def hint_cycle(repo: Repository, learner_id: str, ex: Row) -> tuple[int, int]:
    """(cycle, redo_count) for this learner and lab."""
    state = await repo.get_hint_state(learner_id, ex["id"])
    return (int(state["cycle"]), int(state["redo_count"])) if state else (1, 0)


async def hints_revealed(repo: Repository, learner_id: str, ex: Row, attempt_number: int, cycle: int) -> list[Row]:
    """Reveals that count right now: per cycle for pass/fail labs, per attempt otherwise. Ordered by hint index."""
    rows = await repo.list_hint_reveals_cycle(learner_id, ex["id"], cycle) if is_pass_fail(ex) \
        else await repo.list_hint_reveals(learner_id, ex["id"], attempt_number)
    return sorted(rows, key=lambda r: r["hint_index"])


def lab_state(lecture_state: str, subs: list[Row]) -> str:
    """locked | not_started | in_progress | awaiting_review | needs_retry | passed — from server records only."""
    if lecture_state == "locked":
        return "locked"
    if any(s["status"] == "passed" for s in subs):
        return "passed"
    if not subs:
        return "not_started"
    last = subs[-1]["status"]
    if last == "submitted":
        return "awaiting_review"
    if last in ("queued", "running"):
        return "in_progress"
    if last in ("failed", "runtime_error", "timeout"):
        return "needs_retry"
    return "in_progress"


def mark_quiz(questions: list[Row], responses: dict[str, str]) -> dict[str, Any]:
    """Server-side marking of a question set. Correct option ids are never returned."""
    results, correct_n, earned, total_pts = [], 0, 0.0, 0.0
    for q in sorted(questions, key=lambda x: x["question_order"]):
        pts = float(q.get("points") or 1)
        total_pts += pts
        chosen = responses.get(q["id"])
        ok = chosen is not None and chosen == q["correct_option_id"]
        if ok:
            correct_n += 1
            earned += pts
        results.append({"question_id": q["id"], "question_order": q["question_order"], "selected_option_id": chosen,
                        "correct": ok, "explanation": q.get("explanation") or ""})
    score = round(100 * earned / total_pts, 2) if total_pts else 0.0
    return {"results": results, "correct": correct_n, "total": len(questions), "score": score, "passed": bool(questions) and correct_n == len(questions)}


def validate_upload(answers: dict[str, Any], checklist: list[str]) -> list[dict[str, str]]:
    problems = []
    link = str(answers.get("link") or "").strip()
    if not LINK_RE.match(link):
        problems.append({"field": "link", "issue": "Give the https:// link to your work (a repository, document or deployed app)"})
    ticks = answers.get("checklist")
    if checklist and (not isinstance(ticks, list) or len(ticks) != len(checklist) or not all(isinstance(t, bool) for t in ticks)):
        problems.append({"field": "checklist", "issue": "Tick every item of the checklist you completed (one answer per item)"})
    elif checklist and not all(ticks):
        problems.append({"field": "checklist", "issue": "Every checklist item must be done before you submit"})
    notes = str(answers.get("notes") or "")
    if len(notes) > MAX_TEXT_CHARS:
        problems.append({"field": "notes", "issue": f"Notes are limited to {MAX_TEXT_CHARS} characters"})
    return problems


def public_assets(assets: list[Row]) -> list[Row]:
    """Assets as sent to the browser runtime (bounded)."""
    out = []
    for a in (assets or [])[:40]:
        if not isinstance(a, dict) or not a.get("name"):
            continue
        content = str(a.get("content") or "")[:400_000]
        out.append({"name": str(a["name"])[:120], "encoding": "base64" if a.get("encoding") == "base64" else "text",
                    "content": content, "description": str(a.get("description") or "")[:300]})
    return out


def files_for_sandbox(assets: list[Row]) -> dict[str, Any]:
    files: dict[str, Any] = {}
    for a in public_assets(assets):
        files[a["name"]] = {"encoding": "base64", "content": a["content"]} if a["encoding"] == "base64" else a["content"]
    return files


def limits_for(ex: Row) -> dict[str, Any]:
    lim = ex.get("limits") or {}
    heavy = any(p in (ex.get("packages") or []) for p in ("numpy", "pandas", "matplotlib", "scikit-learn", "sklearn", "pillow"))
    memory = int(lim.get("memory_mb") or (384 if heavy else 128))
    timeout = float(lim.get("timeout_seconds") or (20 if heavy else 5))
    return {"memory_mb": max(64, min(1024, memory)), "timeout_seconds": max(1.0, min(60.0, timeout))}


def visible_checks(tests: list[Row]) -> list[Row]:
    """Non-hidden tests, with their definitions, so the browser can run the quick check. Hidden tests never leave the server."""
    out = []
    for t in sorted(tests, key=lambda x: x["test_order"]):
        if t.get("is_hidden"):
            continue
        out.append({"test_order": t["test_order"], "label": t.get("criterion_label") or str(t["definition"].get("description", f"Check {t['test_order']}")),
                    "definition": t["definition"], "remediation": t.get("remediation"), "objective": t.get("objective")})
    return out
