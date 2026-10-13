"""Staging drills for hosted grading. Run against a DEV project with a synthetic learner and a running worker.

  DEV_USER_PASSWORD=... WORKER_TOKEN_FILE=... API_BASE=https://... SSM_INSTANCE=i-... \
  backend/.venv/bin/python scripts/staging_drills.py [journey|restart|dead-letter|auth|all]

Prints PASS/FAIL per drill with timings; never prints tokens or passwords."""
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
API = os.environ["API_BASE"].rstrip("/") + "/api/v1"
SB, ANON = os.environ["SUPABASE_URL"].rstrip("/"), os.environ["SUPABASE_ANON_KEY"]
WTOKEN = Path(os.environ["WORKER_TOKEN_FILE"]).read_text().strip()
LEARNER = os.getenv("DRILL_LEARNER", "learner3@neuromind.test")
LID, EX = "00000000-0000-4000-8000-000000000009", "00000000-0000-4000-8000-0000000000e1"
GOOD = 'student_name = "Aarav"\nprint(student_name)\n'
BAD = 'print("hello")\n'
FINAL = {"passed", "failed", "runtime_error", "timeout", "error", "expired", "cancelled"}
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""), flush=True)


def login(c: httpx.Client) -> dict:
    r = c.post(f"{SB}/auth/v1/token?grant_type=password", headers={"apikey": ANON},
               json={"email": LEARNER, "password": os.environ["DEV_USER_PASSWORD"]})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def prepare(c: httpx.Client, h: dict) -> None:
    man = c.get(f"{API}/lectures/{LID}", headers=h).json()
    c.get(f"{API}/lectures/{LID}/session", headers=h)
    for seg in man["segments"]:
        cp = seg.get("checkpoint")
        if cp:
            q = cp["question"]
            c.post(f"{API}/checkpoints/{cp['id']}/attempts", headers={**h, "Idempotency-Key": str(uuid.uuid4())},
                   json={"question_id": q["id"], "selected_option_id": q["options"][0]["id"]})


def submit(c: httpx.Client, h: dict, code: str, key: str | None = None) -> str:
    r = c.post(f"{API}/exercises/{EX}/submissions", headers={**h, "Idempotency-Key": key or str(uuid.uuid4())}, json={"source_code": code})
    r.raise_for_status()
    return r.json()["submission_id"]


def wait(c: httpx.Client, h: dict, sid: str, limit: float = 120) -> tuple[dict, float]:
    t0, sub = time.time(), {}
    while time.time() - t0 < limit:
        sub = c.get(f"{API}/submissions/{sid}", headers=h).json()
        if sub.get("status") in FINAL:
            break
        time.sleep(1.5)
    return sub, time.time() - t0


def ssm(cmd: str) -> None:
    subprocess.run(["aws", "ssm", "send-command", "--instance-ids", os.environ["SSM_INSTANCE"], "--document-name", "AWS-RunShellScript",
                    "--region", "ap-southeast-2", "--profile", "neuromind", "--parameters", f"commands=[\"{cmd}\"]"],
                   check=True, capture_output=True)


def worker_call(c: httpx.Client, path: str, body: dict, token: str | None = WTOKEN) -> httpx.Response:
    return c.post(f"{API}/internal/grader/{path}", json=body, headers={"X-Worker-Token": token} if token else {})


def drill_journey(c, h) -> None:
    prepare(c, h)
    s1 = submit(c, h, BAD)
    sub1, t1 = wait(c, h, s1)
    check("wrong code: real worker returns a genuine failure with criteria", sub1.get("status") == "failed" and bool(sub1.get("criteria")), f"{sub1.get('status')} score={sub1.get('score')} {t1:.1f}s end-to-end")
    key = str(uuid.uuid4())
    s2 = submit(c, h, GOOD, key)
    s2b = submit(c, h, GOOD, key)
    check("duplicate submit with the same idempotency key returns the same attempt", s2 == s2b)
    sub2, t2 = wait(c, h, s2)
    check("correct code passes via the worker", sub2.get("status") == "passed" and sub2.get("score") == 100, f"{sub2.get('status')} score={sub2.get('score')} {t2:.1f}s")
    s3 = submit(c, h, BAD)
    sub3, _ = wait(c, h, s3)
    hist = c.get(f"{API}/exercises/{EX}/submissions", headers=h).json()
    check("later worse attempt does not lower the best valid score", hist["best_score"] == 100 and sub3.get("status") == "failed", f"best={hist['best_score']}")
    late = worker_call(c, f"jobs/{s2}/result", {"worker_id": "w-late", "result": {"status": "failed", "passed_tests": 0, "total_tests": 3, "score": 0}})
    after = c.get(f"{API}/submissions/{s2}", headers=h).json()
    check("duplicate/late worker result cannot change a final result", late.status_code == 200 and late.json().get("accepted") is False and after["status"] == "passed", late.text[:80])


def drill_restart(c, h) -> None:
    prepare(c, h)
    sid = submit(c, h, "while True:\n    pass\n")  # runs until the 5 s limit, giving us a window to kill the worker
    time.sleep(2.5)
    ssm("systemctl kill -s SIGKILL neuromind-worker")  # systemd restarts it after 5 s
    sub, t = wait(c, h, sid, 240)
    check("worker killed mid-job: job is re-claimed after lease expiry and finishes", sub.get("status") == "timeout", f"{sub.get('status')} after {t:.0f}s")


def drill_dead_letter(c, h) -> None:
    prepare(c, h)
    ssm("systemctl stop neuromind-worker")
    time.sleep(8)
    sid = submit(c, h, GOOD)
    got = []
    for i in range(3):
        r = worker_call(c, "claim", {"worker_id": f"drill-{i}"})
        got.append(r.status_code)
        if i < 2:
            time.sleep(62)  # lease (60 s) must expire before the next claim
    time.sleep(62)
    fourth = worker_call(c, "claim", {"worker_id": "drill-3"})
    sub, _ = wait(c, h, sid, 10)
    ssm("systemctl start neuromind-worker")
    check("three lost claims dead-letter the job as a system error, not a learner failure",
          got == [200, 200, 200] and fourth.status_code == 204 and sub.get("status") == "error" and sub.get("infrastructure_error") is True and sub.get("score") is None,
          f"claims={got} fourth={fourth.status_code} status={sub.get('status')}")


def drill_auth(c, h) -> None:
    check("claim without a token is rejected", worker_call(c, "claim", {"worker_id": "x-1"}, None).status_code == 401)
    check("claim with a wrong token is rejected", worker_call(c, "claim", {"worker_id": "x-1"}, "wrong").status_code == 401)
    check("a learner session token cannot use the worker interface", c.post(f"{API}/internal/grader/claim", json={"worker_id": "x-1"}, headers=h).status_code == 401)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    with httpx.Client(timeout=30) as c:
        hdr = login(c)
        for name, fn in (("auth", drill_auth), ("journey", drill_journey), ("restart", drill_restart), ("dead-letter", drill_dead_letter)):
            if which in ("all", name):
                print(f"--- {name}", flush=True)
                fn(c, hdr)
    failed = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)} passed, {len(failed)} failed")
    sys.exit(1 if failed else 0)
