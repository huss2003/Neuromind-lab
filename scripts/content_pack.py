"""Validate and import lecture content packs (content/lectures/*.json). One tool for every lecture; no per-lecture scripts.

  backend/.venv/bin/python scripts/content_pack.py validate content/lectures
  backend/.venv/bin/python scripts/content_pack.py import content/lectures --tests private/exercise_tests_10_12.json            # dry run
  backend/.venv/bin/python scripts/content_pack.py import content/lectures/013-x.json --tests private/t.json --yes             # writes as DRAFT
  backend/.venv/bin/python scripts/content_pack.py import content/lectures/013-x.json --tests private/t.json --yes --publish   # writes as published

Hidden test definitions come from --tests files (JSON object: test key -> definition), which stay out of Git (private/).
Import is idempotent: ids are derived from the lecture number, so running it twice updates the same rows.
Needs SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or a sb_secret_ key) in .env for import. Use the DEV project, or production only on purpose.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.content_pack import WRITE_ORDER, PackError, build_rows, check_collection, check_pack, uid  # noqa: E402

DEFAULT_COURSE, DEFAULT_MODULE = "00000000-0000-4000-8000-000000000001", "00000000-0000-4000-8000-000000000002"
COURSE_FILE = ROOT / "content" / "course.json"


def course_spec() -> dict:
    return json.loads(COURSE_FILE.read_text())


def module_for(spec: dict, lecture_number: int) -> str:
    """The month-module a lecture belongs to, from content/course.json (falls back to the default module)."""
    for m in spec.get("modules", []):
        if lecture_number in m.get("lectures", []):
            return m["id"]
    return DEFAULT_MODULE


def _client_and_base():
    import httpx
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    base, key = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1", os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    headers = {"apikey": key, **({} if key.startswith("sb_secret_") else {"Authorization": f"Bearer {key}"}), "Content-Type": "application/json"}
    return httpx.Client(timeout=40), base, headers


def cmd_course(args: argparse.Namespace) -> int:
    """Create/update the course, its month-modules and a DRAFT stub for every lecture that has no record yet (titles from the document).
    Packs imported later replace the stubs. Never unpublishes anything."""
    spec = course_spec()
    c, base, headers = _client_and_base()
    write = {**headers, "Prefer": "resolution=merge-duplicates,return=minimal"}
    with c:
        existing = c.get(f"{base}/lectures", headers=headers, params={"select": "id,lecture_number,status,title", "course_id": f"eq.{spec['id']}"})
        existing.raise_for_status()
        have = {r["lecture_number"]: r for r in existing.json()}
        course = {"id": spec["id"], "slug": spec["slug"], "title": spec["title"], "description": spec["description"], "status": "published"}
        modules = [{"id": m["id"], "course_id": spec["id"], "module_number": m["module_number"], "title": m["title"], "description": m.get("description", ""),
                    "sort_order": m["module_number"], "status": "published"} for m in spec["modules"]]
        stubs = []
        for lec in spec["lectures"]:
            n = lec["number"]
            if n in have:
                continue
            stubs.append({"id": uid(f"lecture{n}"), "course_id": spec["id"], "module_id": module_for(spec, n), "lecture_number": n, "title": lec["title"],
                          "summary": lec["summary"], "learning_objectives": [], "duration_seconds": 3600, "status": "draft", "content_version": 1,
                          "prerequisites": [], "published_at": None})
        print(f"{'WRITE' if args.yes else 'plan '} course '{spec['title']}', {len(modules)} modules, {len(stubs)} new draft lecture stubs "
              f"({len(have)} lectures already exist and are left as they are)")
        if not args.yes:
            return 0
        for table, rows in (("courses", [course]), ("modules", modules), ("lectures", stubs)):
            if not rows:
                continue
            r = c.post(f"{base}/{table}", headers=write, json=rows)
            if r.status_code >= 300:
                print(f"FAIL {table}: HTTP {r.status_code} {r.text[:300]}")
                return 1
        # existing lectures move to their month-module
        for n, row in have.items():
            c.patch(f"{base}/lectures", headers=write, params={"id": f"eq.{row['id']}"}, json={"module_id": module_for(spec, n)}).raise_for_status()
    print("course records written")
    return 0


def collect(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        path = Path(p)
        files += sorted(path.glob("*.json")) if path.is_dir() else [path]
    return files


def load_packs(files: list[Path]):
    packs, problems = [], []
    for f in files:
        try:
            data = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(f"{f}: cannot read JSON ({exc})")
            continue
        pack, errs = check_pack(data)
        if pack is None:
            problems += [f"{f}: {e}" for e in errs]
        else:
            packs.append((f, pack))
    problems += check_collection([p for _, p in packs])
    return packs, problems


def load_tests(paths: list[str]) -> dict[str, dict]:
    merged: dict[str, dict] = {}
    for p in paths:
        merged.update(json.loads(Path(p).read_text()))
    return merged


def cmd_validate(args: argparse.Namespace) -> int:
    files = collect(args.paths)
    if not files:
        print("no pack files found")
        return 1
    packs, problems = load_packs(files)
    for f, p in packs:
        print(f"ok   {f.name}: lecture {p.lecture_number} '{p.title}' ({len(p.segments)} segments, {len(p.lab.tests)} lab tests)")
    for line in problems:
        print(f"FAIL {line}")
    return 1 if problems else 0


def cmd_import(args: argparse.Namespace) -> int:
    import httpx
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    files = collect(args.paths)
    packs, problems = load_packs(files)
    if problems or not packs:
        print("\n".join(f"FAIL {p}" for p in problems) or "no pack files found")
        return 1
    tests = load_tests(args.tests)
    base, key = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1", os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    headers = {"apikey": key, **({} if key.startswith("sb_secret_") else {"Authorization": f"Bearer {key}"}), "Content-Type": "application/json"}
    write_headers = {**headers, "Prefer": "resolution=merge-duplicates,return=minimal"}
    with httpx.Client(timeout=40) as c:
        existing = c.get(f"{base}/lectures", headers=headers, params={"select": "id,lecture_number,status", "course_id": f"eq.{args.course}"})
        existing.raise_for_status()
        by_number = {r["lecture_number"]: r for r in existing.json()}
        ids = {n: r["id"] for n, r in by_number.items()}
        wrote = 0
        for f, pack in sorted(packs, key=lambda x: x[1].lecture_number):
            try:
                module_id = args.module or (module_for(course_spec(), pack.lecture_number) if COURSE_FILE.exists() else DEFAULT_MODULE)
                rows = build_rows(pack, tests, course_id=args.course, module_id=module_id, prerequisite_ids=ids, publish=args.publish)
            except PackError as exc:
                print(f"FAIL {f.name}: {exc}")
                return 1
            ids[pack.lecture_number] = rows["lectures"][0]["id"]
            current = by_number.get(pack.lecture_number)
            if current and current["status"] == "published" and not args.publish and not args.force:
                print(f"SKIP {f.name}: lecture {pack.lecture_number} is published; importing as draft would unpublish it. Use --publish, or --force to unpublish.")
                return 1
            verb = "update" if current else "create"
            print(f"{'WRITE' if args.yes else 'plan '} {f.name}: {verb} lecture {pack.lecture_number} as {'published' if args.publish else 'draft'} "
                  f"({', '.join(f'{t}={len(rows[t])}' for t in WRITE_ORDER)})")
            if not args.yes:
                continue
            for table in WRITE_ORDER:
                r = c.post(f"{base}/{table}", headers=write_headers, json=rows[table])
                if r.status_code >= 300:
                    print(f"FAIL {f.name}: {table}: HTTP {r.status_code} {r.text[:300]}")
                    return 1
            wrote += 1
    print(f"imported {wrote} lecture(s)" if args.yes else "dry run only; add --yes to write")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate", help="check packs offline")
    v.add_argument("paths", nargs="+")
    v.set_defaults(fn=cmd_validate)
    i = sub.add_parser("import", help="write packs to the database (dry run unless --yes)")
    i.add_argument("paths", nargs="+")
    i.add_argument("--tests", action="append", default=[], required=True, help="JSON file mapping test key -> hidden definition (repeatable)")
    i.add_argument("--yes", action="store_true", help="actually write")
    i.add_argument("--publish", action="store_true", help="mark the lecture, questions and exercise as published (default: draft)")
    i.add_argument("--force", action="store_true", help="allow importing a draft over a published lecture")
    i.add_argument("--course", default=DEFAULT_COURSE)
    i.add_argument("--module", default=None, help="module id (default: the month-module from content/course.json)")
    i.set_defaults(fn=cmd_import)
    co = sub.add_parser("course", help="write the course, month-modules and draft lecture stubs from content/course.json (dry run unless --yes)")
    co.add_argument("--yes", action="store_true")
    co.set_defaults(fn=cmd_course)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
