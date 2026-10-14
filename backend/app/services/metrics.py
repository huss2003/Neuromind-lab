"""Queue and grading latency figures from submission timestamps. Queue wait = first claim minus creation; execution = finish minus first claim."""
from datetime import datetime
from typing import Any

Row = dict[str, Any]


def _ts(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    xs = sorted(values)
    return round(xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))], 2)


def summarise(rows: list[Row]) -> dict[str, Any]:
    waits: list[float] = []
    execs: list[float] = []
    totals: list[float] = []
    by_status: dict[str, int] = {}
    for r in rows:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
        created, started, finished = _ts(r.get("created_at")), _ts(r.get("started_at")), _ts(r.get("finished_at"))
        if created and started:
            waits.append(max(0.0, (started - created).total_seconds()))
        if started and finished:
            execs.append(max(0.0, (finished - started).total_seconds()))
        if created and finished:
            totals.append(max(0.0, (finished - created).total_seconds()))
    return {"sample": len(rows), "by_status": by_status,
            "queue_wait_seconds": {"p50": percentile(waits, 50), "p95": percentile(waits, 95), "max": round(max(waits), 2) if waits else None},
            "execution_seconds": {"p50": percentile(execs, 50), "p95": percentile(execs, 95), "max": round(max(execs), 2) if execs else None},
            "end_to_end_seconds": {"p50": percentile(totals, 50), "p95": percentile(totals, 95), "max": round(max(totals), 2) if totals else None}}
