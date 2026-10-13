"""Real-container isolation tests. SKIPPED automatically when Docker or the sandbox image is missing.
Run on the worker host after `docker build -t neuromind-grader-sandbox grader/`:  pytest tests/test_docker_sandbox.py -v
Every probe prints what it found in stdout; the assertions require the probe to have been DENIED."""
import asyncio
import shutil
import subprocess

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


def test_network_is_denied_including_cloud_metadata():
    r = run("import socket\nfor host in ('169.254.169.254', '1.1.1.1', 'example.com'):\n"
            "    try:\n        s = socket.create_connection((host, 80), 2)\n        print('OPEN', host)\n    except Exception as e:\n        print('DENIED', host)\n")
    assert r.status == "ok" and "OPEN" not in r.stdout and r.stdout.count("DENIED") == 3


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


def test_infinite_loop_times_out_and_container_is_removed():
    r = run("while True:\n    pass\n", timeout=2)
    assert r.status == "timeout"
    left = subprocess.run(["docker", "ps", "-a", "--filter", "name=nm-grade-", "-q"], capture_output=True, text=True).stdout.strip()
    assert left == ""


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
