"""Pull-model grading worker. Run it where Docker is available, e.g. `python worker.py`.

It makes OUTBOUND HTTPS calls only (no listening port, nothing to expose) and holds no database credentials:
  claim -> run in the Docker sandbox -> evaluate hidden tests host-side -> post result (heartbeat while running).

Environment: API_BASE_URL (e.g. https://neuromind-lab-api.vercel.app), GRADER_WORKER_TOKEN, WORKER_ID (optional),
WORKER_CONCURRENCY (default 1, max 2), plus the sandbox limits already used by the grader service.
SIGTERM/SIGINT: stop claiming, finish (or release) the current job, exit."""
import asyncio
import os
import random
import signal
import socket
import subprocess
from typing import Any

import httpx

from grader_service.evaluate import GRADER_VERSION, HARNESS_VERSION, evaluate, probe_exprs, required_vars
from grader_service.runner import DockerRunner, probe_image

FAST_POLL, BUSY_WINDOW = 1.0, 60.0  # seconds; adaptive polling keeps idle API traffic low
SLOW_POLL = float(os.getenv("WORKER_IDLE_POLL", "5"))  # idle poll: 5 s is about 520k API calls a month, inside the Vercel free allowance


class Worker:
    def __init__(self, client: httpx.AsyncClient, runner: Any, worker_id: str, capabilities: dict | None = None) -> None:
        self.http, self.runner, self.id = client, runner, worker_id
        self.caps = capabilities or {}
        self.last_job = -1e9
        self.refused = False

    async def _post(self, path: str, body: dict) -> httpx.Response:
        return await self.http.post(path, json={"worker_id": self.id, **body})

    async def _heartbeat(self, sub_id: str, every: float) -> None:
        while True:
            await asyncio.sleep(every)
            try:
                if (await self._post(f"/jobs/{sub_id}/heartbeat", {})).status_code == 409:
                    return  # lease lost: another worker owns it now; our late result will be fenced out
            except httpx.HTTPError:
                pass

    async def process(self, job: dict) -> None:
        sub_id = job["submission_id"]
        beat = asyncio.create_task(self._heartbeat(sub_id, max(5.0, job["lease_seconds"] / 3)))
        try:
            tests = job["tests"]
            limits = job.get("limits") or {}
            run = await self.runner.run(job["source_code"], required_vars(tests), float(limits.get("timeout_seconds") or job["timeout_seconds"]),
                                        files=job.get("files") or {}, probes=probe_exprs(tests), memory_mb=limits.get("memory_mb"),
                                        lab_api="requests" in (job.get("packages") or []))
            result = evaluate(tests, run, float(job["pass_threshold"]))
            result.setdefault("criteria", [])
            result.setdefault("grader_version", GRADER_VERSION)
            await self._post(f"/jobs/{sub_id}/result", {"result": result})
        except Exception:  # noqa: BLE001 - infrastructure problem: hand the job back (the API bounds retries)
            try:
                await self._post(f"/jobs/{sub_id}/release", {})
            except httpx.HTTPError:
                pass  # the lease will expire and the job will be re-claimed
        finally:
            beat.cancel()

    async def run_once(self) -> bool:
        r = await self._post("/claim", {"harness_version": HARNESS_VERSION, "packages": self.caps.get("packages", {}),
                                        "runtime": self.caps.get("runtime"), "python": self.caps.get("python")})
        if r.status_code == 204:
            reason = r.headers.get("X-Claim-Refused")
            if reason and not self.refused:
                print(f"WARNING: the API refuses to give this worker jobs ({reason}). Rebuild the sandbox image and update the worker.", flush=True)
            self.refused = bool(reason)
            return False
        r.raise_for_status()
        self.last_job = asyncio.get_event_loop().time()
        await self.process(r.json())
        return True

    async def run_forever(self, stop: asyncio.Event) -> None:
        errors = 0
        while not stop.is_set():
            try:
                got = await self.run_once()
                errors = 0
            except httpx.HTTPError:
                got, errors = False, errors + 1
            if got:
                continue
            busy = asyncio.get_event_loop().time() - self.last_job < BUSY_WINDOW
            delay = FAST_POLL if busy else SLOW_POLL
            delay = min(60.0, delay * (2 ** min(errors, 5))) * random.uniform(0.8, 1.2)  # backoff + jitter on API errors
            try:
                await asyncio.wait_for(stop.wait(), delay)
            except TimeoutError:
                pass


def sweep_stray_containers() -> None:
    """On start, remove sandbox containers left by an earlier crash. Each carries a hard in-container deadline too; this is the second line."""
    try:
        ids = subprocess.run(["docker", "ps", "-aq", "--filter", "name=nm-grade-"], capture_output=True, text=True, timeout=20).stdout.split()
        if ids:
            subprocess.run(["docker", "rm", "-f", *ids], capture_output=True, timeout=60)
            print(f"removed {len(ids)} stray sandbox container(s)", flush=True)
    except (OSError, subprocess.SubprocessError):
        pass


async def main() -> None:
    sweep_stray_containers()
    base = os.environ["API_BASE_URL"].rstrip("/") + "/api/v1/internal/grader"
    token = os.environ["GRADER_WORKER_TOKEN"]
    wid = os.getenv("WORKER_ID") or f"{socket.gethostname()}-{os.getpid()}"
    n = max(1, min(2, int(os.getenv("WORKER_CONCURRENCY", "1"))))
    stop = asyncio.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        asyncio.get_running_loop().add_signal_handler(sig, stop.set)
    runner = DockerRunner(memory_mb=int(os.getenv("GRADING_MEMORY_MB", "128")), cpus=float(os.getenv("GRADING_CPU_LIMIT", "1")),
                          max_output=int(os.getenv("MAX_OUTPUT_BYTES", "20000")))
    caps = probe_image()  # refuses to start (and systemd retries) if the sandbox image or runtime is unusable
    print(f"sandbox ready: runtime={caps['runtime']} python={caps['python']} packages={caps['packages']}", flush=True)
    async with httpx.AsyncClient(base_url=base, headers={"X-Worker-Token": token}, timeout=30) as client:
        await asyncio.gather(*[Worker(client, runner, f"{wid}-{i}", caps).run_forever(stop) for i in range(n)])


if __name__ == "__main__":
    asyncio.run(main())
