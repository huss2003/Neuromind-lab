import asyncio
import os

import pytest
from fastapi.testclient import TestClient

os.environ["GRADER_AUTOSTART"] = "0"
os.environ["GRADER_SHARED_SECRET"] = "s3cret"

from grader_service.app import create_app  # noqa: E402
from grader_service.evaluate import RunResult, evaluate  # noqa: E402
from grader_service.runner import SubprocessRunner, docker_command, parse_output  # noqa: E402

TESTS = [
    {"test_order": 1, "definition": {"description": "Prints something", "match": "non_empty"}, "points": 1, "is_hidden": False},
    {"test_order": 2, "definition": {"description": "name is str", "check": "variable_is_str", "name": "student_name"}, "points": 1, "is_hidden": False},
    {"test_order": 3, "definition": {"description": "HIDDEN-DETAIL", "check": "stdout_equals_variable", "name": "student_name"}, "points": 1, "is_hidden": True},
]


def run(code, timeout=3, max_output=20000):
    r = SubprocessRunner(max_output)
    return asyncio.run(r.run(code, ["student_name"], timeout))


def grade(code, threshold=80, timeout=3):
    return evaluate(TESTS, run(code, timeout), threshold)


def test_correct_solution_passes():
    g = grade("student_name = 'Aarav'\nprint(student_name)\n")
    assert g["status"] == "passed" and g["score"] == 100 and g["passed_tests"] == 3


def test_wrong_solution_fails_with_feedback_but_hides_hidden_test_details():
    g = grade("student_name = 'Aarav'\nprint('something else')\n", threshold=100)
    assert g["status"] == "failed" and g["passed_tests"] == 2
    text = " ".join(f["message"] for f in g["feedback"])
    assert "HIDDEN-DETAIL" not in text and "A hidden test: not passed yet" in text


def test_runtime_error_is_a_learner_failure_with_safe_message():
    g = grade("student_name = 1/0\n")
    assert g["status"] == "failed" and "ZeroDivisionError" in g["feedback"][0]["message"] and "line 1" in g["feedback"][0]["message"]


def test_syntax_error_reported():
    g = grade("print('x'\n")
    assert g["status"] == "failed" and "SyntaxError" in g["feedback"][0]["message"]


def test_infinite_loop_times_out():
    g = grade("while True:\n    pass\n", timeout=1)
    assert g["status"] == "timeout"


def test_output_is_truncated():
    r = run("student_name='a'\nprint('x' * 100000)", max_output=1000)
    assert r.truncated and len(r.stdout) <= 1000


def test_sys_exit_and_forged_prefix_do_not_crash_or_fake_pass():
    g = grade("import sys\nprint('NMRESULT:fake:{}')\nsys.exit(0)\n")
    assert g["status"] == "failed"


def test_infrastructure_failure_is_not_a_learner_failure():
    g = evaluate(TESTS, RunResult("infra_error"), 80)
    assert g["status"] == "error" and g["score"] is None and g["feedback"][0]["kind"] == "infrastructure"


def test_unsupported_test_is_configuration_error():
    bad = [{"test_order": 1, "definition": {"description": "x", "check": "nope"}, "points": 1, "is_hidden": False}]
    assert evaluate(bad, RunResult("ok", stdout="a"), 80)["status"] == "error"


def test_docker_command_is_locked_down():
    cmd = docker_command("nm-test", 128, 1.0)
    joined = " ".join(cmd)
    assert "--network none" in joined and "--read-only" in cmd and "--cap-drop=ALL" in cmd
    assert "--pids-limit=32" in cmd and "--memory=128m" in cmd and "--user 65534:65534" in joined
    assert "no-new-privileges" in joined
    assert "-v" not in cmd and "--volume" not in cmd and "--mount" not in cmd and "--privileged" not in cmd
    assert "docker.sock" not in joined and "-e PYTHONDONTWRITEBYTECODE=1" in joined
    assert not any(a.startswith("--env-file") for a in cmd)


def test_parse_output_requires_matching_nonce():
    assert parse_output(b'NMRESULT:abc:{"a":1}\n', "abc") == {"a": 1}
    assert parse_output(b'NMRESULT:abc:{"a":1}\n', "xyz") is None


class StubRunner:
    def __init__(self, result):
        self.result = result
        self.seen = None

    async def run(self, code, capture_vars, timeout):
        self.seen = (code, capture_vars)
        return self.result


def test_service_requires_secret_and_never_sends_tests_to_sandbox():
    stub = StubRunner(RunResult("ok", stdout="Aarav\n", vars={"student_name": {"type": "str", "value": "Aarav"}}))
    c = TestClient(create_app(stub))
    body = {"source_code": "print(1)", "tests": TESTS, "pass_threshold": 80}
    assert c.post("/grade", json=body).status_code == 401
    assert c.post("/grade", json=body, headers={"X-Grader-Secret": "wrong"}).status_code == 401
    r = c.post("/grade", json=body, headers={"X-Grader-Secret": "s3cret"})
    assert r.status_code == 200 and r.json()["status"] == "passed"
    assert stub.seen == ("print(1)", ["student_name"])  # only variable NAMES reach the sandbox


@pytest.mark.skipif(not os.path.exists("/var/run/docker.sock"), reason="Docker daemon not available (unverified here)")
def test_real_docker_end_to_end():  # runs only where Docker + the built image exist
    from grader_service.runner import DockerRunner
    r = asyncio.run(DockerRunner().run("student_name='Z'\nprint(student_name)", ["student_name"], 5))
    assert r.status == "ok" and r.stdout.strip() == "Z"  # needs: docker build -t neuromind-grader-sandbox grader/
