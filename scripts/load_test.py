"""Load test against the live (dev) stack with synthetic learners (loadtest01.. created by scripts/create_load_users.py).

Objectives are FIXED BEFORE RUNNING (docs/06-operations/LOAD_TEST_PLAN.md) and the run exits non-zero if one is missed:
  reads  p95 <= 800 ms | writes p95 <= 1000 ms | submission acknowledgement p95 <= 1000 ms | errors <= 1 %
  grading end-to-end p95 <= 30 s (burst of N simultaneous submissions)
Latencies include this machine's network path and TLS; they are an upper bound for in-region users, not a server-side measure.

  DEV_USER_PASSWORD=... API_BASE=https://... USERS=40 STAGES=10,25,40 HOLD=60 BURST=12 backend/.venv/bin/python scripts/load_test.py"""
import asyncio
import os
import re
import random
import statistics
import sys
import time
import uuid
from collections import defaultdict
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
API = os.environ["API_BASE"].rstrip("/") + "/api/v1"
SB, ANON = os.environ["SUPABASE_URL"].rstrip("/"), os.environ["SUPABASE_ANON_KEY"]
PW = os.environ["DEV_USER_PASSWORD"]
USERS = int(os.getenv("USERS", "40"))
STAGES = [int(x) for x in os.getenv("STAGES", "10,25,40").split(",")]
HOLD = float(os.getenv("HOLD", "60"))
BURST = int(os.getenv("BURST", "12"))
LID, EX = "00000000-0000-4000-8000-000000000009", "00000000-0000-4000-8000-0000000000e1"
GOOD = 'student_name = "Aarav"\nprint(student_name)\n'
OBJ = {"read": 800, "write": 1000, "submit_ack": 1000}
lat: dict[str, list[float]] = defaultdict(list)
errs: dict[str, int] = defaultdict(int)
calls: dict[str, int] = defaultdict(int)
srv: dict[str, list[float]] = defaultdict(list)  # server-side total from the Server-Timing header (excludes the network path)
err_codes: dict[int, int] = defaultdict(int)


async def timed(kind: str, c: httpx.AsyncClient, method: str, url: str, **kw) -> httpx.Response | None:
    t = time.perf_counter()
    try:
        r = await c.request(method, url, **kw)
        ms = (time.perf_counter() - t) * 1000
        calls[kind] += 1
        if r.status_code >= 500 or r.status_code in (401, 403):
            errs[kind] += 1
            err_codes[r.status_code] += 1
        else:
            lat[kind].append(ms)
            m = re.search(r"total;dur=([\d.]+)", r.headers.get("server-timing", ""))
            if m:
                srv[kind].append(float(m.group(1)))
        return r
    except httpx.HTTPError as exc:
        calls[kind] += 1
        errs[kind] += 1
        err_codes[-1] += 1
        print(f"  transport error on {kind}: {type(exc).__name__}")
        return None


class VU:
    def __init__(self, i: int) -> None:
        self.email = f"loadtest{i:02d}@neuromind.test"
        self.h: dict = {}
        self.cp: list[tuple[str, str, str]] = []

    async def login(self, c: httpx.AsyncClient) -> bool:
        for attempt in range(4):
            r = await c.post(f"{SB}/auth/v1/token?grant_type=password", headers={"apikey": ANON}, json={"email": self.email, "password": PW})
            if r.status_code == 200:
                self.h = {"Authorization": f"Bearer {r.json()['access_token']}"}
                return True
            await asyncio.sleep(3 * (attempt + 1))
        return False

    async def setup(self, c: httpx.AsyncClient) -> None:
        man = (await c.get(f"{API}/lectures/{LID}", headers=self.h)).json()
        await c.get(f"{API}/lectures/{LID}/session", headers=self.h)
        self.first_segment = man["segments"][0]["id"]
        self.cp = [(s["checkpoint"]["id"], s["checkpoint"]["question"]["id"], s["checkpoint"]["question"]["options"][0]["id"]) for s in man["segments"] if s.get("checkpoint")]

    async def loop(self, c: httpx.AsyncClient, stop: float) -> None:
        while time.time() < stop:
            await timed("read:dashboard", c, "GET", f"{API}/me/dashboard", headers=self.h)
            await timed("read:course", c, "GET", f"{API}/courses", headers=self.h)
            await timed("read:lecture", c, "GET", f"{API}/lectures/{LID}", headers=self.h)
            r = await timed("read:session", c, "GET", f"{API}/lectures/{LID}/session", headers=self.h)
            if r is not None and r.status_code == 200:
                ver = r.json().get("state_version")
                await timed("write:session", c, "PATCH", f"{API}/lectures/{LID}/session", headers=self.h,
                            json={"current_segment_id": self.first_segment, "playback_position_seconds": random.randint(0, 5), "state_version": ver})
            if self.cp:
                cp, q, o = random.choice(self.cp)
                await timed("write:checkpoint", c, "POST", f"{API}/checkpoints/{cp}/attempts", headers={**self.h, "Idempotency-Key": str(uuid.uuid4())},
                            json={"question_id": q, "selected_option_id": o})
            await timed("write:draft", c, "PUT", f"{API}/exercises/{EX}/draft", headers=self.h, json={"source_code": GOOD + f"# {random.random()}\n"})
            await asyncio.sleep(random.uniform(1, 3))  # think time


def pct(xs: list[float], p: float) -> float:
    if not xs:
        return float("nan")
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def report(title: str) -> dict[str, float]:
    print(f"\n== {title}")
    print(f"{'endpoint':20s} {'n':>6s} {'err':>5s} {'p50':>7s} {'p95':>7s} {'p99':>7s}  (ms)  | server-side p50 / p95")
    p95s: dict[str, float] = {}
    for k in sorted(set(lat) | set(errs)):
        xs = lat.get(k, [])
        p95s[k] = pct(xs, 95)
        print(f"{k:20s} {calls[k]:6d} {errs[k]:5d} {pct(xs, 50):7.0f} {pct(xs, 95):7.0f} {pct(xs, 99):7.0f}  | {pct(srv.get(k, []), 50):5.0f} / {pct(srv.get(k, []), 95):5.0f}")
    return p95s


async def stage(vus: list[VU], n: int) -> dict[str, float]:
    lat.clear()
    errs.clear()
    calls.clear()
    srv.clear()
    err_codes.clear()
    async with httpx.AsyncClient(timeout=30, limits=httpx.Limits(max_connections=200)) as c:
        t0 = time.time()
        await asyncio.gather(*[v.loop(c, t0 + HOLD) for v in vus[:n]])
    total, bad = sum(calls.values()), sum(errs.values())
    print(f"\nstage {n} users: {total} requests in {HOLD:.0f}s ({total / HOLD:.1f} req/s), errors {bad} ({100 * bad / max(total, 1):.2f}%)")
    if err_codes:
        print(f"  error status codes (-1 = transport): {dict(err_codes)}")
    return report(f"{n} concurrent learners")


async def burst(vus: list[VU], n: int) -> tuple[list[float], list[float], int]:
    async with httpx.AsyncClient(timeout=60) as c:
        for v in vus[:n]:  # unlock the lab through the normal checkpoint path
            for cp, q, o in v.cp:
                await c.post(f"{API}/checkpoints/{cp}/attempts", headers={**v.h, "Idempotency-Key": str(uuid.uuid4())}, json={"question_id": q, "selected_option_id": o})
        acks: list[float] = []
        totals: list[float] = []
        failed = 0

        async def one(v: VU) -> None:
            nonlocal failed
            t = time.perf_counter()
            r = await c.post(f"{API}/exercises/{EX}/submissions", headers={**v.h, "Idempotency-Key": str(uuid.uuid4())}, json={"source_code": GOOD})
            acks.append((time.perf_counter() - t) * 1000)
            if r.status_code != 202:
                failed += 1
                return
            sid = r.json()["submission_id"]
            while time.perf_counter() - t < 180:
                s = (await c.get(f"{API}/submissions/{sid}", headers=v.h)).json()
                if s.get("status") in ("passed", "failed", "runtime_error", "timeout", "error", "expired", "cancelled"):
                    if s["status"] != "passed":
                        failed += 1
                    totals.append(time.perf_counter() - t)
                    return
                await asyncio.sleep(1.5)
            failed += 1
        await asyncio.gather(*[one(v) for v in vus[:n]])
    return acks, totals, failed


async def main() -> int:
    vus = [VU(i) for i in range(1, USERS + 1)]
    sem = asyncio.Semaphore(4)
    async with httpx.AsyncClient(timeout=httpx.Timeout(30, connect=60)) as c:
        async def prep(v: VU) -> bool:
            for attempt in range(3):  # the load generator reaches the internet through a proxy; a failed handshake is not an API result
                try:
                    async with sem:
                        ok = await v.login(c)
                        if ok:
                            await v.setup(c)
                    return ok
                except httpx.TransportError:
                    await asyncio.sleep(2 * (attempt + 1))
            return False
        ok = await asyncio.gather(*[prep(v) for v in vus])
    vus = [v for v, k in zip(vus, ok, strict=True) if k]
    print(f"{len(vus)} of {USERS} learners signed in")
    failures: list[str] = []
    for n in STAGES:
        if n > len(vus):
            continue
        p95 = await stage(vus, n)
        for k, v in p95.items():
            kind = k.split(":")[0]
            if kind in OBJ and v > OBJ[kind]:
                failures.append(f"{n} users: {k} p95 {v:.0f} ms > {OBJ[kind]} ms")
        bad, total = sum(errs.values()), sum(calls.values())
        if total and bad / total > 0.01:
            failures.append(f"{n} users: error rate {100 * bad / total:.2f}% > 1%")
    n = min(BURST, len(vus))
    print(f"\n== submission burst: {n} learners submit at the same moment")
    acks, totals, failed = await burst(vus, n)
    print(f"ack p50 {pct(acks, 50):.0f} ms, p95 {pct(acks, 95):.0f} ms | grading end to end p50 {pct(totals, 50):.1f} s, p95 {pct(totals, 95):.1f} s, max {max(totals, default=0):.1f} s | not passed/failed requests: {failed}")
    if pct(acks, 95) > OBJ["submit_ack"]:
        failures.append(f"burst: ack p95 {pct(acks, 95):.0f} ms > {OBJ['submit_ack']} ms")
    if totals and pct(totals, 95) > 30:
        failures.append(f"burst: grading p95 {pct(totals, 95):.1f} s > 30 s")
    if failed:
        failures.append(f"burst: {failed} submissions did not finish as passed")
    print("\nRESULT:", "PASS" if not failures else "FAIL")
    for f in failures:
        print(" -", f)
    _ = statistics
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
