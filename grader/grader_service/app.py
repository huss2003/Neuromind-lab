"""Private grading service. Bind to 127.0.0.1 only; never expose publicly."""
import hmac
import os
from typing import Any, Protocol

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from grader_service.evaluate import RunResult, evaluate, required_vars
from grader_service.runner import DockerRunner


class Runner(Protocol):
    async def run(self, code: str, capture_vars: list[str], timeout: float) -> RunResult: ...


class TestIn(BaseModel):
    test_order: int
    definition: dict[str, Any]
    points: float = Field(gt=0)
    is_hidden: bool = False


class GradeIn(BaseModel):
    source_code: str = Field(max_length=100_000)
    tests: list[TestIn] = Field(min_length=1, max_length=50)
    pass_threshold: float = Field(ge=0, le=100)
    timeout_seconds: float = Field(default=5, gt=0, le=30)


def create_app(runner: Runner | None = None) -> FastAPI:
    app = FastAPI(title="NeuroMind grader (private)")
    runner = runner or DockerRunner(
        memory_mb=int(os.getenv("GRADING_MEMORY_MB", "128")), cpus=float(os.getenv("GRADING_CPU_LIMIT", "1")),
        max_output=int(os.getenv("MAX_OUTPUT_BYTES", "20000")))
    semaphore_size = int(os.getenv("GRADER_MAX_PARALLEL", "2"))
    import asyncio
    sem = asyncio.Semaphore(semaphore_size)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/grade")
    async def grade(body: GradeIn, x_grader_secret: str | None = Header(default=None)) -> dict:
        expected = os.getenv("GRADER_SHARED_SECRET", "")
        if not expected or not x_grader_secret or not hmac.compare_digest(expected, x_grader_secret):
            raise HTTPException(401)
        tests = [t.model_dump() for t in body.tests]
        async with sem:  # bounded concurrency: this is a laptop, not a worker pool
            run = await runner.run(body.source_code, required_vars(tests), body.timeout_seconds)
        return evaluate(tests, run, body.pass_threshold)

    return app


app = create_app() if os.getenv("GRADER_AUTOSTART", "1") == "1" else None
