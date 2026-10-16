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


def _clear_children(c, base: str, headers: dict, lecture_id: str, force: bool) -> bool:
    """Replace mode: remove a lecture's sections, checkpoints, questions, lab, checks and quiz questions so the pack's
    deterministic ids can take their place. Refuses when learners already have attempts, unless --force."""
    h = {**headers, "Prefer": "return=minimal"}
    ex_ids = [e["id"] for e in c.get(f"{base}/lecture_exercises", headers=headers, params={"lecture_id": f"eq.{lecture_id}", "select": "id"}).json()]
    if ex_ids:
        subs = c.get(f"{base}/lab_submissions", headers={**headers, "Prefer": "count=exact"}, params={"exercise_id": f"in.({','.join(ex_ids)})", "select": "id", "limit": "1"})
        n = int(subs.headers.get("content-range", "0-0/0").split("/")[-1] or 0)
        if n and not force:
            print(f"FAIL lecture {lecture_id}: {n} learner attempt(s) reference its lab; replacing would delete them. Use --force only if that is intended.")
            return False
    cps = c.get(f"{base}/lecture_checkpoints", headers=headers, params={"lecture_id": f"eq.{lecture_id}", "select": "question_id"}).json()
    att = c.get(f"{base}/checkpoint_attempts", headers={**headers, "Prefer": "count=exact"}, params={"checkpoint_id": f"in.({','.join(x['question_id'] for x in cps) or 'x'})", "select": "id", "limit": "1"}) if cps else None
    for table, params in (("lecture_segments", {"lecture_id": f"eq.{lecture_id}"}),
                          ("lecture_checkpoints", {"lecture_id": f"eq.{lecture_id}"}),
                          ("mcq_questions", {"id": f"in.({','.join(x['question_id'] for x in cps)})"} if cps else None),
                          ("exercise_tests", {"exercise_id": f"in.({','.join(ex_ids)})"} if ex_ids else None),
                          ("lab_questions", {"exercise_id": f"in.({','.join(ex_ids)})"} if ex_ids else None),
                          ("lecture_exercises", {"lecture_id": f"eq.{lecture_id}"})):
        if params is None:
            continue
        r = c.delete(f"{base}/{table}", headers=h, params=params)
        if r.status_code >= 300:
            print(f"FAIL clearing {table}: HTTP {r.status_code} {r.text[:300]}")
            return False
    del att
    return True


def cmd_export(args: argparse.Namespace) -> int:
    """Write a lecture that exists in the database as a pack (and its hidden checks as a private file), so it can be edited and re-imported."""
    c, base, headers = _client_and_base()
    with c:
        lec = c.get(f"{base}/lectures", headers=headers, params={"lecture_number": f"eq.{args.number}", "course_id": f"eq.{args.course}", "select": "*"}).json()
        if not lec:
            print("no such lecture")
            return 1
        lec = lec[0]
        segs = c.get(f"{base}/lecture_segments", headers=headers, params={"lecture_id": f"eq.{lec['id']}", "select": "*", "order": "segment_order"}).json()
        cps = c.get(f"{base}/lecture_checkpoints", headers=headers, params={"lecture_id": f"eq.{lec['id']}", "select": "*", "order": "checkpoint_order"}).json()
        qs = {q["id"]: q for q in c.get(f"{base}/mcq_questions", headers=headers, params={"id": f"in.({','.join(x['question_id'] for x in cps) or 'x'})", "select": "*"}).json()} if cps else {}
        exs = c.get(f"{base}/lecture_exercises", headers=headers, params={"lecture_id": f"eq.{lec['id']}", "select": "*"}).json()
        ex = exs[0] if exs else None
        tests = c.get(f"{base}/exercise_tests", headers=headers, params={"exercise_id": f"eq.{ex['id']}", "select": "*", "order": "test_order"}).json() if ex else []
        lqs = c.get(f"{base}/lab_questions", headers=headers, params={"exercise_id": f"eq.{ex['id']}", "select": "*", "order": "question_order"}).json() if ex else []
    n = lec["lecture_number"]
    seg_key = {s["id"]: f"seg-{s['segment_order']}" for s in segs}
    cp_key = {cp["id"]: f"cp{cp['checkpoint_order']}" for cp in cps}
    pack = {"schema_version": 2, "lecture_number": n, "title": lec["title"], "summary": lec["summary"] or lec["title"], "objectives": lec.get("learning_objectives") or [lec["title"]],
            "duration_minutes": max(5, int((lec.get("duration_seconds") or 3600) / 60)), "prerequisites": [], "lab_only": not cps,
            "checkpoints": [{"key": cp_key[cp["id"]], "type": cp["checkpoint_type"], "question": {"prompt": qs[cp["question_id"]]["prompt"], "options": qs[cp["question_id"]]["options"],
                             "correct_option_id": qs[cp["question_id"]]["correct_option_id"], "explanation_correct": qs[cp["question_id"]]["explanation_correct"],
                             "explanation_incorrect": qs[cp["question_id"]].get("explanation_incorrect") or qs[cp["question_id"]]["explanation_correct"],
                             "shuffle_options": bool(qs[cp["question_id"]].get("shuffle_options"))}} for cp in cps],
            "segments": [{"key": seg_key[s["id"]], "type": s["segment_type"], "title": s["title"], **({"body": (s.get("settings") or {}).get("body")} if (s.get("settings") or {}).get("body") else {}),
                          **({"checkpoint": cp_key[s["checkpoint_id"]]} if s.get("checkpoint_id") else {}), **({"opens_exercise": True} if (s.get("settings") or {}).get("on_end") else {})} for s in segs]}
    hidden = {}
    if ex:
        lab = {"kind": ex.get("lab_kind") or "code", "scoring": ex.get("scoring") or "score", "title": ex["title"], "objective": ex.get("objective") or ex["title"], "instructions": ex["instructions"],
               "constraints": ex.get("constraints") or "", "starter_code": ex["starter_code"], "hints": ex.get("hints") or [], "hints_max": ex.get("hints_max") or 3,
               "hint_penalty_percent": int(float(ex.get("hint_penalty_percent") or 0)), "pass_threshold": int(float(ex["pass_threshold"])), "practice_mode": ex.get("practice_mode") or "both",
               "packages": ex.get("packages") or [], "assets": ex.get("assets") or [], "limits": ex.get("limits") or {}, "visible_examples": ex.get("visible_examples") or [],
               "success_criteria": ex.get("success_criteria") or [ex["title"]], "rubric": ex.get("rubric") or [], "checklist": ex.get("checklist") or [],
               "questions": [{"prompt": q["prompt"], "options": q["options"], "correct_option_id": q["correct_option_id"], "explanation": q.get("explanation") or "", "points": int(float(q.get("points") or 1))} for q in lqs],
               "tests": [], "solution": "# TODO: add the reference solution before re-importing\n"}
        for t in tests:
            key = f"l{n}-t{t['test_order']}"
            entry = {"key": key, "label": t.get("criterion_label") or "", "remediation": t.get("remediation") or "Check the lesson again.", "objective": t.get("objective") or "Lab", "hidden": bool(t["is_hidden"]),
                     "remediation_segment": seg_key.get(t.get("remediation_segment_id"))}
            if t["is_hidden"]:
                hidden[key] = t["definition"]
            else:
                entry["definition"] = t["definition"]
            lab["tests"].append(entry)
        pack["lab"] = lab
    out = Path(args.out)
    out.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n")
    if hidden:
        priv = Path(args.private or (ROOT / "private" / f"exercise_tests_l{n}.json"))
        priv.write_text(json.dumps(hidden, indent=2) + "\n")
        print(f"hidden checks -> {priv}")
    print(f"exported lecture {n} -> {out}")
    return 0


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
                current = by_number.get(pack.lecture_number)
                rows = build_rows(pack, tests, course_id=args.course, module_id=module_id, prerequisite_ids=ids, publish=args.publish,
                                  lecture_id=current["id"] if current else None)
            except PackError as exc:
                print(f"FAIL {f.name}: {exc}")
                return 1
            ids[pack.lecture_number] = rows["lectures"][0]["id"]
            current = by_number.get(pack.lecture_number)
            if current and current["status"] == "published" and not args.publish and not args.force:
                print(f"SKIP {f.name}: lecture {pack.lecture_number} is published; importing as draft would unpublish it. Use --publish, or --force to unpublish.")
                return 1
            verb = "replace" if current and args.replace else "update" if current else "create"
            print(f"{'WRITE' if args.yes else 'plan '} {f.name}: {verb} lecture {pack.lecture_number} as {'published' if args.publish else 'draft'} "
                  f"({', '.join(f'{t}={len(rows[t])}' for t in WRITE_ORDER)})")
            if not args.yes:
                continue
            if current and args.replace and not _clear_children(c, base, headers, current["id"], args.force):
                return 1
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
    i.add_argument("--force", action="store_true", help="allow importing a draft over a published lecture / replacing content that learners already attempted")
    i.add_argument("--replace", action="store_true", help="replace the lecture's existing sections, checks and lab (keeps the lecture id)")
    i.add_argument("--course", default=DEFAULT_COURSE)
    i.add_argument("--module", default=None, help="module id (default: the month-module from content/course.json)")
    i.set_defaults(fn=cmd_import)
    ex = sub.add_parser("export", help="export a lecture from the database as a pack")
    ex.add_argument("number", type=int)
    ex.add_argument("--out", required=True)
    ex.add_argument("--private", default=None, help="where to write hidden checks (default private/exercise_tests_l<N>.json)")
    ex.add_argument("--course", default=DEFAULT_COURSE)
    ex.set_defaults(fn=cmd_export)
    co = sub.add_parser("course", help="write the course, month-modules and draft lecture stubs from content/course.json (dry run unless --yes)")
    co.add_argument("--yes", action="store_true")
    co.set_defaults(fn=cmd_course)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
