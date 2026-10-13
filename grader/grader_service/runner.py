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


def docker_command(name: str, memory_mb: int, cpus: float, image: str = IMAGE, limit_seconds: int = 10) -> list[str]:
    """Strict, secret-free `docker run` invocation. No mounts, no network, no inherited environment."""
    return [
        "docker", "run", "--rm", "-i", "--name", name,
        "--network", "none",
        f"--memory={memory_mb}m", f"--memory-swap={memory_mb}m", f"--cpus={cpus}",
        "--pids-limit=32", "--ulimit", "nofile=64:64", "--ulimit", "fsize=1000000:1000000",
        "--read-only", "--tmpfs", "/tmp:rw,noexec,nosuid,size=8m",
        "--cap-drop=ALL", "--security-opt", "no-new-privileges",
        "--user", "65534:65534",
        "-e", "PYTHONDONTWRITEBYTECODE=1",
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


async def _drive(cmd: list[str], payload: dict, timeout: float, kill_cmd: list[str] | None) -> tuple[int | None, bytes, int, bool]:
    start = time.monotonic()
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, env={})
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


def _to_result(code: int | None, out: bytes, ms: int, timed_out: bool, nonce: str) -> RunResult:
    if timed_out:
        return RunResult("timeout", execution_ms=ms)
    parsed = parse_output(out, nonce)
    if parsed:
        return RunResult("ok", parsed["stdout"], parsed["truncated"], parsed["error"], parsed["vars"], ms)
    if code in (125, 126, 127):  # docker itself failed / image missing / binary missing
        return RunResult("infra_error", execution_ms=ms, detail=f"docker exit {code}")
    if code == 137:
        return RunResult("crashed", execution_ms=ms, detail="Your program used too much memory and was stopped.")
    return RunResult("crashed", execution_ms=ms, detail="Your program ended without finishing normally.")


class DockerRunner:
    def __init__(self, memory_mb: int = 128, cpus: float = 1.0, max_output: int = 20_000):
        self.memory_mb, self.cpus, self.max_output = memory_mb, cpus, max_output

    async def run(self, code: str, capture_vars: list[str], timeout: float) -> RunResult:
        nonce = secrets.token_hex(16)
        name = f"nm-grade-{uuid.uuid4().hex[:12]}"
        payload = {"code": code, "capture_vars": capture_vars, "nonce": nonce, "max_output": self.max_output}
        try:
            # Wall-clock limit includes container start-up; kill + --rm cleans the container.
            result = await _drive(docker_command(name, self.memory_mb, self.cpus, limit_seconds=int(timeout) + 3), payload, timeout + 3,
                                  ["docker", "kill", name])
        except (FileNotFoundError, PermissionError, OSError):
            return RunResult("infra_error", detail="docker unavailable")
        return _to_result(*result, nonce)


class SubprocessRunner:
    """TEST ONLY. No isolation."""

    def __init__(self, max_output: int = 20_000):
        self.max_output = max_output

    async def run(self, code: str, capture_vars: list[str], timeout: float) -> RunResult:
        nonce = secrets.token_hex(16)
        payload = {"code": code, "capture_vars": capture_vars, "nonce": nonce, "max_output": self.max_output}
        result = await _drive([sys.executable, "-I", str(HARNESS)], payload, timeout, None)
        return _to_result(*result, nonce)
