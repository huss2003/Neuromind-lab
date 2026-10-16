"""The worker against a fake API (httpx MockTransport) and the non-isolated runner. Docker is NOT used here."""
import asyncio
import json

import httpx

from grader_service.runner import SubprocessRunner
from worker import Worker

TESTS = [{"test_order": 1, "points": 1, "is_hidden": False, "definition": {"match": "non_empty"}},
         {"test_order": 2, "points": 1, "is_hidden": True, "definition": {"check": "variable_is_str", "name": "student_name"}}]


def job(code):
    return {"submission_id": "s1", "claim_count": 1, "lease_seconds": 60, "source_code": code, "pass_threshold": 80,
            "timeout_seconds": 5, "tests": TESTS}


def api(jobs):
    seen = []

    def handler(req: httpx.Request) -> httpx.Response:
        path = req.url.path
        body = json.loads(req.content or b"{}")
        seen.append((path, body))
        if path.endswith("/claim"):
            return httpx.Response(200, json=jobs.pop(0)) if jobs else httpx.Response(204)
        return httpx.Response(200, json={"accepted": True})
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://api.test"), seen


def test_worker_grades_a_job_and_posts_the_result():
    client, seen = api([job('student_name = "A"\nprint(student_name)\n')])

    async def go():
        async with client:
            w = Worker(client, SubprocessRunner(), "w-1")
            assert await w.run_once() is True
            assert await w.run_once() is False
    asyncio.run(go())
    posted = [b for p, b in seen if p.endswith("/result")][0]
    assert posted["worker_id"] == "w-1" and posted["result"]["status"] == "passed" and posted["result"]["score"] == 100


def test_worker_releases_the_job_when_the_runner_blows_up():
    class Boom:
        async def run(self, *a, **k):
            raise RuntimeError("docker exploded")
    client, seen = api([job("x = 1")])

    async def go():
        async with client:
            await Worker(client, Boom(), "w-1").run_once()
    asyncio.run(go())
    assert [p for p, _ in seen if p.endswith("/release")] and not [p for p, _ in seen if p.endswith("/result")]


def test_infrastructure_failure_is_never_posted_as_a_learner_result():
    class Down:
        async def run(self, code, names, timeout, **kwargs):
            from grader_service.evaluate import RunResult
            return RunResult("infra_error", detail="docker unavailable")
    client, seen = api([job("x = 1")])

    async def go():
        async with client:
            await Worker(client, Down(), "w-1").run_once()
    asyncio.run(go())
    res = [b for p, b in seen if p.endswith("/result")][0]["result"]
    assert res["status"] == "error" and res["score"] is None
