"""Teacher/admin evidence views (§9). Teachers see only currently assigned learners; admins see all.
There is intentionally NO endpoint that edits an official score; feedback is a separate record."""
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from app.auth import CurrentUser, require_roles
from app.errors import ApiError
from app.repository import Repository, get_repository
from app.routers.deps import path_uuid
from app.routers.exercises import can_view_learner
from app.services import audit
from app.services.grading import best_valid_score

router = APIRouter(prefix="/api/v1/teacher")
guard = require_roles("teacher", "admin")


async def _scope(user: CurrentUser, repo: Repository) -> list[str] | None:
    """None = unrestricted (admin)."""
    return None if user.role == "admin" else await repo.list_assigned_learner_ids(user.id)


@router.get("/summary")
async def summary(user: CurrentUser = Depends(guard), repo: Repository = Depends(get_repository)):
    ids = await _scope(user, repo)
    learners, total = await repo.list_learners_page(ids, None, 100, 0)
    completed = in_progress = passed = infra = failed = 0
    for lr in learners:
        for s in await repo.list_learner_sessions(lr["id"]):
            completed += s["status"] == "completed"
            in_progress += s["status"] == "in_progress"
        for sub in await repo.list_learner_submissions(lr["id"]):
            passed += sub["status"] == "passed"
            infra += sub["status"] == "error"
            failed += sub["status"] in ("failed", "timeout")
    return {"assigned_learners": total, "lectures_completed": completed, "lectures_in_progress": in_progress,
            "submissions_passed": passed, "submissions_needing_retry": failed, "infrastructure_failures": infra}


SUPPORT_AFTER_FAILURES = 3  # evaluated failures on one exercise without a pass => "needs support"


async def _summary(repo: Repository, learner_id: str) -> dict[str, Any]:
    sessions = await repo.list_learner_sessions(learner_id)
    subs = await repo.list_learner_submissions(learner_id)
    by_ex: dict[str, list[dict]] = {}
    for s in subs:
        by_ex.setdefault(s["exercise_id"], []).append(s)
    stuck = [e for e, rows in by_ex.items() if not any(r["status"] == "passed" for r in rows)
             and sum(r["status"] in ("failed", "runtime_error") for r in rows) >= SUPPORT_AFTER_FAILURES]
    last = max((str(s["last_seen_at"]) for s in sessions), default=None)
    return {"lectures_completed": sum(s["status"] == "completed" for s in sessions),
            "lectures_in_progress": sum(s["status"] == "in_progress" for s in sessions),
            "needs_support": bool(stuck), "grader_problems": sum(x["status"] in ("error", "expired") for x in subs),
            "last_active": last}


@router.get("/learners")
async def learners(q: str | None = Query(default=None, max_length=50), limit: int = Query(default=25, ge=1, le=100),
                   offset: int = Query(default=0, ge=0), needs_support: bool = False,
                   progress: Literal["any", "not_started", "in_progress", "completed"] = "any",
                   user: CurrentUser = Depends(guard), repo: Repository = Depends(get_repository)):
    scope = await _scope(user, repo)
    if needs_support or progress != "any":  # derived filters: computed over the whole scope (bounded), then paged
        rows, _ = await repo.list_learners_page(scope, q, 100, 0)
        enriched = [{"id": r["id"], "display_name": r["display_name"], **await _summary(repo, r["id"])} for r in rows]
        if needs_support:
            enriched = [e for e in enriched if e["needs_support"]]
        if progress == "completed":
            enriched = [e for e in enriched if e["lectures_completed"] > 0]
        elif progress == "in_progress":
            enriched = [e for e in enriched if e["lectures_in_progress"] > 0]
        elif progress == "not_started":
            enriched = [e for e in enriched if e["lectures_completed"] == 0 and e["lectures_in_progress"] == 0]
        return {"learners": enriched[offset:offset + limit], "total": len(enriched), "limit": limit, "offset": offset}
    rows, total = await repo.list_learners_page(scope, q, limit, offset)
    out = [{"id": r["id"], "display_name": r["display_name"], **await _summary(repo, r["id"])} for r in rows]
    return {"learners": out, "total": total, "limit": limit, "offset": offset}


@router.get("/analytics/exercises")
async def exercise_analytics(user: CurrentUser = Depends(guard), repo: Repository = Depends(get_repository)):
    """§13.1: completion rate, score distribution, common failing criteria and grading-system errors per exercise."""
    rows, _ = await repo.list_learners_page(await _scope(user, repo), None, 100, 0)
    per: dict[str, dict[str, Any]] = {}
    for lr in rows:
        for s in await repo.list_learner_submissions(lr["id"]):
            d = per.setdefault(s["exercise_id"], {"learners": set(), "passed_learners": set(), "attempts": 0, "scores": [],
                                                  "system_errors": 0, "fails": {}})
            d["learners"].add(lr["id"])
            d["attempts"] += 1
            if s["status"] == "passed":
                d["passed_learners"].add(lr["id"])
            if s["status"] in ("error", "expired"):
                d["system_errors"] += 1
            if s["status"] in ("passed", "failed", "runtime_error") and s.get("score") is not None:
                d["scores"].append(float(s["score"]))
            for c in s.get("criteria_results") or []:
                if not c.get("passed"):
                    d["fails"][c["label"]] = d["fails"].get(c["label"], 0) + 1
    titles = await repo.titles([], [], list(per))
    out = []
    for ex, d in per.items():
        sc = d["scores"]
        out.append({
            "exercise_id": ex, "exercise": titles["exercises"].get(ex), "attempts": d["attempts"],
            "learners": len(d["learners"]), "completion_rate": round(100 * len(d["passed_learners"]) / len(d["learners"]), 1),
            "average_score": round(sum(sc) / len(sc), 1) if sc else None, "system_errors": d["system_errors"],
            "score_distribution": {"below_50": sum(x < 50 for x in sc), "50_to_79": sum(50 <= x < 80 for x in sc),
                                   "80_and_above": sum(x >= 80 for x in sc)},
            "common_failures": [{"criterion": k, "count": v} for k, v in sorted(d["fails"].items(), key=lambda kv: -kv[1])[:5]],
        })
    return {"exercises": out}


@router.get("/content-status")
async def content_status(_: CurrentUser = Depends(guard), repo: Repository = Depends(get_repository)):
    """§13.1: which content version learners are currently using (read-only; authoring is not enabled)."""
    return {"lectures": [{"id": x["id"], "lecture_number": x["lecture_number"], "title": x["title"], "status": x["status"],
                          "version": x["content_version"]} for x in await repo.list_all_lectures()]}


def _sub_row(s: dict, titles: dict) -> dict[str, Any]:
    return {
        "submission_id": s["id"], "exercise_id": s["exercise_id"], "exercise": titles["exercises"].get(s["exercise_id"]),
        "number": s["submission_number"], "status": s["status"],
        "score": float(s["score"]) if s["score"] is not None else None,
        "raw_score": float(s["raw_score"]) if s.get("raw_score") is not None else None,
        "hints_used": s.get("hints_used") or 0, "passed_tests": s["passed_tests"], "total_tests": s["total_tests"],
        "infrastructure_failure": s["status"] == "error", "created_at": s["created_at"],
    }


@router.get("/learners/{learner_id}/results")
async def learner_results(learner_id: str, request: Request, user: CurrentUser = Depends(guard),
                          repo: Repository = Depends(get_repository)):
    learner_id = path_uuid(learner_id)
    profile = await repo.get_profile(learner_id)
    if not profile or not await can_view_learner(user, learner_id, repo):
        raise ApiError(404, "NOT_FOUND")  # unassigned learners look identical to missing ones
    sessions = await repo.list_learner_sessions(learner_id)
    attempts = await repo.list_learner_attempts(learner_id)
    subs = await repo.list_learner_submissions(learner_id)
    titles = await repo.titles([s["lecture_id"] for s in sessions], sorted({a["checkpoint_id"] for a in attempts}),
                               sorted({s["exercise_id"] for s in subs}))
    feedback = await repo.list_feedback(learner_id, published_only=False)
    by_exercise: dict[str, list] = {}
    for s in subs:
        by_exercise.setdefault(s["exercise_id"], []).append(s)
    await audit.record(repo, request, user.id, "teacher.view_learner", "learner", learner_id)
    return {
        "learner": {"id": profile["id"], "display_name": profile["display_name"]},
        "sessions": [{"lecture_id": s["lecture_id"], "lecture": titles["lectures"].get(s["lecture_id"]),
                      "status": s["status"], "completed_at": s["completed_at"], "last_seen_at": s["last_seen_at"]}
                     for s in sessions],
        "checkpoint_attempts": [{"checkpoint_id": a["checkpoint_id"], "checkpoint": titles["checkpoints"].get(a["checkpoint_id"]),
                                 "is_correct": a["is_correct"], "score": float(a["score"]),
                                 "submitted_at": a["submitted_at"]} for a in attempts],
        "submissions": [_sub_row(s, titles) for s in subs],
        "best_scores": [{"exercise_id": e, "exercise": titles["exercises"].get(e), "best_score": best_valid_score(v)}
                        for e, v in by_exercise.items()],
        "feedback": [{"id": f["id"], "body": f["body"], "published": f["published"], "created_at": f["created_at"],
                      "submission_id": f.get("submission_id")} for f in feedback],
    }


@router.get("/submissions/{submission_id}")
async def submission_detail(submission_id: str, request: Request, user: CurrentUser = Depends(guard),
                            repo: Repository = Depends(get_repository)):
    sub = await repo.get_submission(path_uuid(submission_id))
    if not sub or not await can_view_learner(user, sub["learner_id"], repo):
        raise ApiError(404, "NOT_FOUND")
    titles = await repo.titles([], [], [sub["exercise_id"]])
    await audit.record(repo, request, user.id, "teacher.view_submission", "submission", sub["id"],
                       {"submission_id": sub["id"]})
    return {**_sub_row(sub, titles), "source_code": sub["source_code"], "max_score": float(sub.get("max_score") or 100),
            "pass_threshold": float(sub["pass_threshold"]) if sub.get("pass_threshold") is not None else None,
            "hint_penalty": float(sub.get("hint_penalty") or 0), "criteria": sub.get("criteria_results") or [],
            "feedback_messages": sub["safe_feedback"], "execution_ms": sub["execution_ms"],
            "evidence": {"grader_version": sub.get("grader_version"), "test_suite_version": sub.get("test_suite_version"),
                         "content_version": sub.get("content_version"), "correlation_id": sub.get("correlation_id"),
                         "started_at": sub.get("started_at"), "finished_at": sub.get("finished_at")}}


class FeedbackBody(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    submission_id: str | None = None
    lecture_id: str | None = None
    publish: bool = False


@router.post("/learners/{learner_id}/feedback", status_code=201)
async def add_feedback(learner_id: str, body: FeedbackBody, request: Request, user: CurrentUser = Depends(guard),
                       repo: Repository = Depends(get_repository)):
    """Feedback attaches to a learner/activity. It cannot alter any official score."""
    learner_id = path_uuid(learner_id)
    if not await repo.get_profile(learner_id) or not await can_view_learner(user, learner_id, repo):
        raise ApiError(404, "NOT_FOUND")
    if body.submission_id:
        sub = await repo.get_submission(path_uuid(body.submission_id))
        if not sub or sub["learner_id"] != learner_id:
            raise ApiError(422, "VALIDATION_ERROR", details=[{"field": "submission_id", "issue": "Not this learner's submission"}])
    row = await repo.insert_feedback({
        "learner_id": learner_id, "author_id": user.id, "body": body.body.strip(), "published": body.publish,
        "published_at": audit_now() if body.publish else None, "submission_id": body.submission_id,
        "lecture_id": body.lecture_id})
    await audit.record(repo, request, user.id, "feedback.created", "feedback", row["id"], {"published": body.publish})
    return {"id": row["id"], "published": row["published"]}


def audit_now() -> str:
    from datetime import UTC, datetime
    return datetime.now(UTC).isoformat()
