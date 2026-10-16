"""Sandbox runners. DockerRunner is the only runner the service uses.

`SubprocessRunner` exists for unit tests of harness/evaluation logic on machines without Docker; it gives NO isolation
and must never be wired into the service.
"""
import asyncio
import json
import os
import secrets
import sys
import time
import uuid
from pathlib import Path

from grader_service.evaluate import RunResult

HARNESS = Path(__file__).resolve().parents[1] / "sandbox" / "harness.py"
IMAGE = os.getenv("GRADER_IMAGE", "neuromind-grader-sandbox")


MIN_MEMORY_MB, MAX_MEMORY_MB = 64, 1024


def docker_command(name: str, memory_mb: int, cpus: float, image: str = IMAGE, limit_seconds: int = 10, lab_api: bool = False) -> list[str]:
    """Strict, secret-free `docker run` invocation. No mounts, no network, no inherited environment.
    /tmp (tmpfs) holds the learner's working directory with the lab's data files and the Matplotlib cache."""
    memory_mb = max(MIN_MEMORY_MB, min(MAX_MEMORY_MB, int(memory_mb)))
    return [
        "docker", "run", "--rm", "-i", "--name", name,
        "--network", "none",
        f"--memory={memory_mb}m", f"--memory-swap={memory_mb}m", f"--cpus={cpus}",
        "--pids-limit=48", "--ulimit", "nofile=128:128", "--ulimit", "fsize=5000000:5000000",
        "--read-only", "--tmpfs", "/tmp:rw,noexec,nosuid,size=48m",
        "--cap-drop=ALL", "--security-opt", "no-new-privileges",
        "--user", "65534:65534",
        "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "HOME=/tmp", "-e", "MPLBACKEND=Agg", "-e", "MPLCONFIGDIR=/tmp/mpl",
        "-e", "OPENBLAS_NUM_THREADS=1", "-e", "OMP_NUM_THREADS=1", "-e", f"NM_LAB_API={'1' if lab_api else '0'}",
        # Hard in-container deadline, independent of the worker: even if the worker is killed, the program cannot outlive it.
        image, "timeout", "-s", "KILL", str(int(limit_seconds)), "python", "-I", "/app/harness.py",
    ]


def parse_output(raw: bytes, nonce: str) -> dict | None:
    prefix = f"NMRESULT:{nonce}:"
    for line in reversed(raw.decode("utf-8", "replace").splitlines()):
        if line.startswith(prefix):
            try:
                return json.loads(line[len(prefix):])
            except ValueError:
                return None
    return None


async def _drive(cmd: list[str], payload: dict, timeout: float, kill_cmd: list[str] | None, env: dict | None = None) -> tuple[int | None, bytes, int, bool]:
    start = time.monotonic()
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, env=env or {})
    timed_out = False
    try:
        out, _ = await asyncio.wait_for(proc.communicate(json.dumps(payload).encode()), timeout)
    except TimeoutError:
        timed_out = True
        if kill_cmd:
            k = await asyncio.create_subprocess_exec(*kill_cmd, stdout=asyncio.subprocess.DEVNULL,
                                                     stderr=asyncio.subprocess.DEVNULL, env={"PATH": os.environ.get("PATH", "")})
            await k.wait()
        proc.kill()
        out = b""
        await proc.wait()
    return proc.returncode, out[:200_000], int((time.monotonic() - start) * 1000), timed_out


def _to_result(code: int | None, out: bytes, ms: int, timed_out: bool, nonce: str, probe_exprs: list[str] | None = None) -> RunResult:
    if timed_out:
        return RunResult("timeout", execution_ms=ms)
    parsed = parse_output(out, nonce)
    if parsed:
        probes = parsed.get("probes") or []
        return RunResult("ok", parsed["stdout"], parsed["truncated"], parsed["error"], parsed["vars"], ms,
                         probes={e: p for e, p in zip(probe_exprs or [], probes, strict=False) if isinstance(p, dict)})
    if code in (125, 126, 127):  # docker itself failed / image missing / binary missing
        return RunResult("infra_error", execution_ms=ms, detail=f"docker exit {code}")
    if code == 137:
        return RunResult("crashed", execution_ms=ms, detail="Your program used too much memory and was stopped.")
    return RunResult("crashed", execution_ms=ms, detail="Your program ended without finishing normally.")


def _payload(code: str, capture_vars: list[str], nonce: str, max_output: int, files: dict | None, probes: list[str] | None) -> dict:
    return {"code": code, "capture_vars": capture_vars, "nonce": nonce, "max_output": max_output,
            "files": files or {}, "probes": probes or []}


class DockerRunner:
    def __init__(self, memory_mb: int = 128, cpus: float = 1.0, max_output: int = 20_000):
        self.memory_mb, self.cpus, self.max_output = memory_mb, cpus, max_output

    async def run(self, code: str, capture_vars: list[str], timeout: float, *, files: dict | None = None, probes: list[str] | None = None,
                  memory_mb: int | None = None, lab_api: bool = False) -> RunResult:
        nonce = secrets.token_hex(16)
        name = f"nm-grade-{uuid.uuid4().hex[:12]}"
        payload = _payload(code, capture_vars, nonce, self.max_output, files, probes)
        try:
            # Wall-clock limit includes container start-up; kill + --rm cleans the container.
            result = await _drive(docker_command(name, memory_mb or self.memory_mb, self.cpus, limit_seconds=int(timeout) + 3, lab_api=lab_api),
                                  payload, timeout + 3, ["docker", "kill", name])
        except (FileNotFoundError, PermissionError, OSError):
            return RunResult("infra_error", detail="docker unavailable")
        return _to_result(*result, nonce, probes)


class SubprocessRunner:
    """TEST ONLY. No isolation. Also used by the content pipeline to verify reference solutions locally."""

    def __init__(self, max_output: int = 20_000):
        self.max_output = max_output

    async def run(self, code: str, capture_vars: list[str], timeout: float, *, files: dict | None = None, probes: list[str] | None = None,
                  memory_mb: int | None = None, lab_api: bool = False) -> RunResult:
        nonce = secrets.token_hex(16)
        payload = _payload(code, capture_vars, nonce, self.max_output, files, probes)
        env = {"PATH": os.environ.get("PATH", ""), "NM_LAB_API": "1" if lab_api else "0"}
        result = await _drive([sys.executable, "-I", str(HARNESS)], payload, timeout, None, env=env)
        return _to_result(*result, nonce, probes)
