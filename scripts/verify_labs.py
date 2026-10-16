"""Prove every lab pack works before it is imported: the pack validates, its reference solution PASSES every check and its
starter code does NOT pass (so the lab cannot be passed by doing nothing). Runs the real harness in a local subprocess
with the lab's files, packages and the simulated practice API; library labs need grader/requirements-labs.txt installed.

  backend/.venv/bin/python scripts/verify_labs.py content/lectures [--tests private/exercise_tests_block1.json ...] [--numbers 9-24]
Hidden definitions come from --tests files (default: every private/exercise_tests*.json that exists). Without them, hidden
checks are skipped and the run is reported as PARTIAL (CI runs that way; the full run happens locally before an import)."""
from __future__ import annotations

import argparse
import asyncio
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "grader"))

from app.content_pack import build_rows, check_pack  # noqa: E402
from app.services.labs import files_for_sandbox, limits_for  # noqa: E402
from grader_service.evaluate import evaluate, probe_exprs, required_vars  # noqa: E402
from grader_service.runner import SubprocessRunner  # noqa: E402


def parse_numbers(spec: str | None) -> set[int] | None:
    if not spec:
        return None
    out: set[int] = set()
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out.update(range(int(a), int(b or a) + 1))
    return out


async def grade(code: str, tests: list[dict], ex: dict) -> dict:
    lim = limits_for(ex)
    run = await SubprocessRunner().run(code, required_vars(tests), lim["timeout_seconds"], files=files_for_sandbox(ex.get("assets") or []),
                                       probes=probe_exprs(tests), lab_api="requests" in (ex.get("packages") or []))
    return evaluate(tests, run, float(ex["pass_threshold"])) | {"_run_error": run.error, "_stdout": run.stdout[:300]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--tests", action="append", default=None)
    ap.add_argument("--numbers", default=None, help="e.g. 9-24 or 9,12")
    args = ap.parse_args()
    test_files = args.tests if args.tests is not None else sorted(glob.glob(str(ROOT / "private" / "exercise_tests*.json")))
    hidden: dict[str, dict] = {}
    for f in test_files:
        hidden.update(json.loads(Path(f).read_text()))
    files: list[Path] = []
    for p in args.paths:
        path = Path(p)
        files += sorted(path.glob("*.json")) if path.is_dir() else [path]
    wanted = parse_numbers(args.numbers)
    problems, partial, checked = [], False, 0
    for f in files:
        pack, errs = check_pack(json.loads(f.read_text()))
        if errs:
            problems.append(f"{f.name}: " + "; ".join(errs))
            continue
        if wanted and pack.lecture_number not in wanted:
            continue
        if pack.lab.kind != "code":
            print(f"ok   {f.name}: {pack.lab.kind} lab (no code to run)")
            checked += 1
            continue
        defs = dict(hidden)
        missing = [t.key for t in pack.lab.tests if t.key not in defs and t.definition is None]
        if missing:
            partial = True
            tests_used = [t for t in pack.lab.tests if t.key in defs or t.definition is not None]
            print(f"part {f.name}: {len(missing)} hidden check(s) unavailable here ({', '.join(missing)}); verifying the rest")
            pack.lab.tests = tests_used  # type: ignore[misc]
        try:
            rows = build_rows(pack, defs, course_id="verify", module_id="verify")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{f.name}: {exc}")
            continue
        ex, tests = rows["lecture_exercises"][0], rows["exercise_tests"]
        if not tests:
            print(f"skip {f.name}: no runnable checks available")
            continue
        sol = asyncio.run(grade(pack.lab.solution or "", tests, ex))
        start = asyncio.run(grade(pack.lab.starter_code or "pass", tests, ex))
        failed = [c["test_order"] for c in sol.get("criteria", []) if not c["passed"]]
        if sol["status"] != "passed" or failed:
            problems.append(f"{f.name}: the reference solution does not pass (status {sol['status']}, failed checks {failed}, error {sol.get('_run_error')}, feedback {[x['message'] for x in sol['feedback']][:4]})")
        if start["status"] == "passed":
            problems.append(f"{f.name}: the STARTER code already passes every check; the lab asks nothing")
        for t in pack.lab.tests:
            if len(t.remediation) < 5:
                problems.append(f"{f.name}: check {t.key} has no remediation text")
        print(f"{'FAIL' if any(f.name in p for p in problems) else 'ok  '} {f.name}: solution {sol['status']} {sol['passed_tests']}/{sol['total_tests']}, starter {start['status']} {start['passed_tests']}/{start['total_tests']}")
        checked += 1
    for p in problems:
        print("FAIL " + p)
    print(f"{checked} lab(s) checked, {len(problems)} problem(s){' — PARTIAL: hidden checks were not available' if partial else ''}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
