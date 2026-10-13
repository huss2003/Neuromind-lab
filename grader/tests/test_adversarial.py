"""Adversarial tests for the result-integrity boundary (harness parent/child split).

These run the real harness in a LOCAL subprocess, so they prove the forgery boundary and fail-safe parsing, NOT
container isolation (CPU/memory/network/filesystem limits need the Docker sandbox, which is tested separately and
is skipped when Docker is unavailable).
"""
import asyncio


from grader_service.evaluate import evaluate
from grader_service.runner import SubprocessRunner

TESTS = [
    {"test_order": 1, "points": 1, "is_hidden": True, "definition": {"match": "non_empty"}},
    {"test_order": 2, "points": 1, "is_hidden": True, "definition": {"check": "variable_is_str", "name": "student_name"}},
    {"test_order": 3, "points": 1, "is_hidden": True, "definition": {"check": "stdout_equals_variable", "name": "student_name"}},
]


def grade(code: str, timeout: float = 5.0):
    run = asyncio.run(SubprocessRunner().run(code, ["student_name"], timeout))
    return run, evaluate(TESTS, run, 80)


def test_honest_solution_passes():
    _, res = grade('student_name = "Aarav"\nprint(student_name)\n')
    assert res["status"] == "passed" and res["score"] == 100


def test_printing_a_fake_result_line_does_not_pass():
    code = 'print("NMRESULT:00:{\\"stdout\\":\\"x\\",\\"truncated\\":false,\\"error\\":null,\\"vars\\":{}}")\n'
    run, res = grade(code)
    # The fake line is just output: it earns only the "printed something" criterion, never a pass, and the parser ignored it.
    assert res["status"] == "failed" and res["score"] < 100 and run.vars == {}


def test_guessing_or_hunting_the_nonce_in_the_frame_stack_fails():
    code = (
        "import sys, inspect, json\n"
        "found = []\n"
        "f = sys._getframe()\n"
        "while f:\n"
        "    found += [v for v in f.f_locals.values() if isinstance(v, str) and len(v) == 32]\n"
        "    f = f.f_back\n"
        "n = found[0] if found else '0' * 32\n"
        "print('NMRESULT:' + n + ':' + json.dumps({'stdout': 'Aarav', 'truncated': False, 'error': None, "
        "'vars': {'student_name': {'type': 'str', 'value': 'Aarav'}}}))\n"
    )
    run, res = grade(code)
    assert res["status"] == "failed" and res["score"] < 100 and run.vars == {}
    assert "NMRESULT" in run.stdout  # it is captured as ordinary output, not treated as control data


def test_parent_memory_and_environment_do_not_contain_the_nonce():
    code = (
        "import os\n"
        "leak = []\n"
        "for p in ('/proc/%d/environ' % os.getppid(), '/proc/%d/cmdline' % os.getppid(), '/proc/%d/mem' % os.getppid()):\n"
        "    try:\n"
        "        leak.append(open(p, 'rb').read(200000))\n"
        "    except Exception as e:\n"
        "        leak.append(b'')\n"
        "print(len(b''.join(leak)))\n"
        "student_name = 'x'\n"
    )
    run, _ = grade(code)
    assert run.status == "ok"
    assert run.stdout.strip() in {"0", ""} or int(run.stdout.strip()) < 5000  # no readable parent memory


def test_forged_report_on_fd3_with_wrong_shape_fails_safe():
    code = "import os, sys\nos.write(int(sys.argv[1]), b'{\"error\": null, \"vars\": 7}')\nos._exit(0)\n"
    run, res = grade(code)
    assert run.status == "crashed" and res["score"] == 0


def test_abrupt_exit_without_report_fails_safe():
    run, res = grade("import os\nos._exit(0)\n")
    assert run.status == "crashed" and res["status"] == "failed" and res["score"] == 0


def test_sys_exit_is_a_runtime_error_not_a_pass():
    _, res = grade('student_name = "x"\nprint("x")\nimport sys\nsys.exit(0)\n')
    assert res["runtime_error"] is True and res["status"] == "failed"


def test_report_for_undeclared_variable_is_rejected():
    code = "import os, sys, json\nos.write(int(sys.argv[1]), json.dumps({'error': None, 'vars': {'other': {'type': 'str', 'value': 'x'}}}).encode())\nos._exit(0)\n"
    run, _ = grade(code)
    assert run.status == "crashed"


def test_output_flood_is_bounded():
    run, _ = grade('for _ in range(20000):\n    print("A" * 1000)\nstudent_name = "x"\n', timeout=20)
    assert run.truncated is True and len(run.stdout) <= 20_000


def test_endless_output_flood_ends_at_the_time_limit():
    run, res = grade('while True:\n    print("A" * 1000)\n', timeout=2)
    assert run.status == "timeout" and res["status"] == "timeout"


def test_infinite_loop_times_out():
    run, res = grade("while True:\n    pass\n", timeout=1.0)
    assert run.status == "timeout" and res["status"] == "timeout"


def test_invalid_unicode_in_output_is_handled():
    run, _ = grade("import sys\nsys.stdout.buffer.write(b'\\xff\\xfe')\nstudent_name = 'x'\n")
    assert run.status in {"ok", "crashed"}


def test_student_cannot_read_stdin_payload():
    run, _ = grade("import sys\nstudent_name = repr(sys.stdin.read())\nprint(student_name)\n")
    assert "capture_vars" not in run.stdout and "nonce" not in run.stdout


def test_exception_in_student_code_is_reported_with_line_number():
    run, _ = grade("x = 1\nraise ValueError('boom')\n")
    assert run.error and run.error["type"] == "ValueError" and run.error["line"] == 2
