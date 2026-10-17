"""Container runtime selection (gVisor or plain Docker) and the image probe contract. No Docker needed."""
import pytest

from grader_service import runner


def test_default_runtime_is_plain_docker(monkeypatch):
    monkeypatch.delenv("GRADER_RUNTIME", raising=False)
    assert "--runtime=runc" in runner.docker_command("n", 128, 1.0)


def test_gvisor_runtime_is_used_when_configured(monkeypatch):
    monkeypatch.setenv("GRADER_RUNTIME", "runsc")
    cmd = runner.docker_command("n", 128, 1.0)
    assert "--runtime=runsc" in cmd and "--network" in cmd and cmd[cmd.index("--network") + 1] == "none"


@pytest.mark.parametrize("bad", ["runsc --privileged", "--privileged", "kata", "runc;rm"])
def test_unknown_runtime_values_are_refused(monkeypatch, bad):
    monkeypatch.setenv("GRADER_RUNTIME", bad)
    with pytest.raises(ValueError):
        runner.docker_command("n", 128, 1.0)


def test_isolation_flags_are_always_present(monkeypatch):
    monkeypatch.setenv("GRADER_RUNTIME", "runsc")
    cmd = " ".join(runner.docker_command("n", 4096, 1.0))
    for flag in ("--network none", "--read-only", "--cap-drop=ALL", "no-new-privileges", "--user 65534:65534", "--pids-limit=48",
                 "--memory-swap=1024m", "noexec"):
        assert flag in cmd, flag  # memory is clamped to 1024 MB even if a lab asks for more


def test_probe_source_reports_every_lab_package():
    ns: dict = {}
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(runner.PROBE_SOURCE, ns)  # runs in this environment: reports whatever of the six packages is installed here
    import json
    report = json.loads(buf.getvalue())
    assert set(report) == {"python", "packages"} and set(report["packages"]) <= set(runner.LAB_PACKAGES)
