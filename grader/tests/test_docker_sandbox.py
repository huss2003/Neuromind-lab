"""Real-container isolation tests. SKIPPED automatically when Docker or the sandbox image is missing.
Run on the worker host after `docker build -t neuromind-grader-sandbox grader/`:  pytest tests/test_docker_sandbox.py -v
Every probe prints what it found in stdout; the assertions require the probe to have been DENIED."""
import asyncio
import shutil
import subprocess
import time

import pytest

from grader_service.runner import DockerRunner


def _ready() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        return subprocess.run(["docker", "image", "inspect", "neuromind-grader-sandbox"], capture_output=True, timeout=20).returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


pytestmark = pytest.mark.skipif(not _ready(), reason="Docker or the neuromind-grader-sandbox image is not available")


def run(code: str, timeout: float = 8.0, memory_mb: int = 128):
    return asyncio.run(DockerRunner(memory_mb=memory_mb, cpus=1.0).run(code, [], timeout))


HOSTS = ("169.254.169.254", "1.1.1.1", "example.com", "192.168.1.1", "192.168.0.1", "10.0.0.1", "172.17.0.1", "host.docker.internal",
         "neuromind-lab-api.vercel.app", "ddiwlgbllhwcdykqjfne.supabase.co")


def test_network_is_denied_including_cloud_metadata_the_home_network_the_host_api_and_database():
    r = run("import socket\nfor host in %r:\n" % (HOSTS,)
            + "    try:\n        s = socket.create_connection((host, 443), 2)\n        print('OPEN', host)\n    except Exception as e:\n        print('DENIED', host)\n",
            timeout=40)
    assert r.status == "ok" and "OPEN" not in r.stdout and r.stdout.count("DENIED") == len(HOSTS)


def test_only_the_loopback_interface_exists():
    r = run("import socket\nprint(sorted(n for _, n in socket.if_nameindex()))")
    assert r.status == "ok" and r.stdout.strip() == "['lo']"


def test_one_job_cannot_see_files_left_by_another():
    first = run("open('/tmp/secret_of_job_1.txt', 'w').write('mine')\nprint('written')")
    second = run("import os\nprint(os.listdir('/tmp'))")
    assert first.stdout.strip() == "written" and "secret_of_job_1" not in second.stdout


def test_hidden_expected_values_never_enter_the_sandbox():
    """Probe EXPRESSIONS go in; the expected answers stay with the trusted evaluator."""
    from grader_service.evaluate import evaluate, probe_exprs, required_vars
    tests = [{"test_order": 1, "points": 1, "is_hidden": True, "definition": {"expr": "total", "expected": 4242}}]
    # the program computes 4242 without writing it, then prints everything it can see; the answer must not appear
    code = "import sys, os\ntotal = 4000 + 242\nprint(open('/proc/self/cmdline').read(), sys.argv, list(os.environ.values()), os.listdir('/tmp'), os.listdir('/app'))"
    r = asyncio.run(DockerRunner().run(code, required_vars(tests), 8, probes=probe_exprs(tests)))
    assert r.status == "ok" and "4242" not in r.stdout and "expected" not in r.stdout
    assert evaluate(tests, r, 80)["status"] == "passed"


def test_lab_libraries_load_and_compute_inside_the_sandbox():
    code = ("import numpy as np, pandas as pd, sklearn, matplotlib.pyplot as plt\n"
            "df = pd.DataFrame({'a': [1, 2, 3]})\nplt.plot([1, 2]); plt.savefig('c.png')\n"
            "print(int(np.arange(4).sum()), int(df['a'].sum()), sklearn.__version__)")
    r = run(code, timeout=20, memory_mb=384)
    assert r.status == "ok" and r.error is None and r.stdout.split()[:2] == ["6", "6"], (r.stdout, r.error)


def test_practice_api_works_and_every_real_host_stays_blocked():
    import json as _json
    from grader_service.runner import docker_command, parse_output
    code = ("import requests\nr = requests.get('https://api.neuromind.lab/v1/weather', params={'city': 'Pune'})\nprint(r.status_code)\n"
            "try:\n    requests.get('https://example.com', timeout=3)\n    print('REAL-OPEN')\nexcept Exception:\n    print('REAL-BLOCKED')")
    cmd = docker_command("nm-grade-api-test", 384, 1.0, limit_seconds=20, lab_api=True)
    out = subprocess.run(cmd, input=_json.dumps({"code": code, "capture_vars": [], "nonce": "n1", "max_output": 2000, "files": {}, "probes": []}).encode(),
                         capture_output=True, timeout=60).stdout
    parsed = parse_output(out, "n1")
    assert parsed and parsed["stdout"].split() == ["200", "REAL-BLOCKED"], parsed


def test_environment_has_no_secrets():
    r = run("import os\nprint(sorted(k for k in os.environ if k not in ('PATH', 'PYTHONDONTWRITEBYTECODE', 'HOME', 'LANG', 'GPG_KEY', 'PYTHON_VERSION', 'PYTHON_SHA256')))")
    assert r.status == "ok" and "KEY" not in r.stdout and "TOKEN" not in r.stdout and "SECRET" not in r.stdout


def test_root_filesystem_is_read_only_and_host_files_are_absent():
    r = run("import os\ntry:\n    open('/app/harness.py', 'a').write('x')\n    print('WROTE')\nexcept Exception:\n    print('READONLY')\n"
            "print(os.path.exists('/var/run/docker.sock'), os.path.exists('/etc/neuromind'), os.path.exists('/opt/neuromind'), os.listdir('/home'))")
    # /home exists (empty) in the base image; what matters is that no host path or socket is visible.
    assert "WROTE" not in r.stdout and "READONLY" in r.stdout and "False False False []" in r.stdout


def test_runs_as_unprivileged_user_without_capabilities():
    r = run("import os\nprint(os.getuid())\ntry:\n    os.setuid(0)\n    print('ROOT')\nexcept Exception:\n    print('NOROOT')")
    assert r.stdout.split()[0] == "65534" and "ROOT\n" not in r.stdout.replace("NOROOT", "")


def test_tmp_is_noexec_and_small():
    r = run("import os, subprocess\np='/tmp/x.sh'\nopen(p,'w').write('#!/bin/sh\\necho hi\\n'); os.chmod(p,0o755)\n"
            "try:\n    subprocess.run([p], check=True)\n    print('EXEC')\nexcept Exception:\n    print('NOEXEC')\n"
            "try:\n    open('/tmp/big','wb').write(b'0'*50_000_000)\n    print('BIG')\nexcept Exception:\n    print('SMALL')")
    assert "NOEXEC" in r.stdout and "SMALL" in r.stdout and "EXEC\n" not in r.stdout.replace("NOEXEC", "")


def _sandbox_ids() -> set[str]:
    return set(subprocess.run(["docker", "ps", "-aq", "--filter", "name=nm-grade-"], capture_output=True, text=True).stdout.split())


def test_infinite_loop_times_out_and_container_is_removed():
    before = _sandbox_ids()  # a live worker on the same host may own other containers
    r = run("while True:\n    pass\n", timeout=2)
    assert r.status == "timeout"
    # `docker kill` returns before the daemon has finished `--rm`; allow that removal a short, bounded time (a CI run showed the race).
    deadline = time.monotonic() + 10
    while _sandbox_ids() - before and time.monotonic() < deadline:
        time.sleep(0.2)
    assert _sandbox_ids() - before == set()


def test_memory_bomb_is_killed_not_graded_as_success():
    r = run("x = []\nwhile True:\n    x.append(' ' * 10_000_000)\n", timeout=10, memory_mb=64)
    assert r.status in {"crashed", "timeout"}


def test_fork_bomb_is_contained_by_the_pid_limit():
    r = run("import os\nn = 0\nwhile n < 500:\n    try:\n        if os.fork() == 0:\n            import time; time.sleep(3); os._exit(0)\n        n += 1\n    except OSError:\n        break\nprint('forks', n)\n", timeout=8)
    assert r.status in {"ok", "crashed", "timeout"}
    if r.status == "ok":
        assert int(r.stdout.split()[-1]) < 100


def test_output_flood_is_bounded():
    r = run("for _ in range(100000):\n    print('A' * 1000)\n", timeout=15)
    assert len(r.stdout) <= 20_000


def test_container_cannot_outlive_its_deadline_even_if_the_worker_is_killed():
    """Start a container the way the worker does, kill the client (as a SIGKILLed worker would), and prove the program still dies."""
    import time
    from grader_service.runner import docker_command
    name = "nm-grade-deadline-test"
    cmd = docker_command(name, 128, 1.0, limit_seconds=3)
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    proc.stdin.write(b'{"code": "while True:\\n    pass\\n", "capture_vars": [], "nonce": "n", "max_output": 100}')
    proc.stdin.close()
    time.sleep(1)
    proc.kill()  # the "worker" dies; the container keeps running unless it has its own deadline
    time.sleep(6)
    left = subprocess.run(["docker", "ps", "-aq", "--filter", f"name={name}"], capture_output=True, text=True).stdout.strip()
    subprocess.run(["docker", "rm", "-f", name], capture_output=True)
    assert left == ""
