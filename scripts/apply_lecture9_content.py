"""Apply the Lecture 9 content (same data as database/seed/005_lecture9_content.sql) through the REST API with the service role.
Use when pasting the SQL is impractical. DEV project only. Needs SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env."""
import importlib.util
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
spec = importlib.util.spec_from_file_location("gen", ROOT / "tools" / "gen_seed_005.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)  # also regenerates the .sql file from the same constants

URL, KEY = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1", os.environ["SUPABASE_SERVICE_ROLE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "Prefer": "return=minimal"}
S = lambda n: f"00000000-0000-4000-8000-{n}"  # noqa: E731


def patch(c: httpx.Client, table: str, id_: str, body: dict) -> None:
    r = c.patch(f"{URL}/{table}", params={"id": f"eq.{id_}"}, json=body, headers=H)
    r.raise_for_status()
    print(f"ok {table} {id_[-4:]}")


def opts(*pairs):
    return [{"id": k, "text": v} for k, v in pairs]


with httpx.Client(timeout=30) as c:
    patch(c, "courses", S("000000000001"), {"title": "NeuroMind AI Foundations", "description": "A practical path from your first Python program to building and understanding AI systems. You learn by writing code that is graded fairly, with help the moment you need it."})
    patch(c, "modules", S("000000000002"), {"title": "Python for AI", "description": "Set up your tools and write the code that every later lecture builds on."})
    patch(c, "lectures", S("000000000009"), {"summary": "Set up Python, run your first notebook cell, and write a program that stores and prints information.",
          "learning_objectives": ["Check that Python is installed and working", "Run code cells and text cells in a notebook", "Store a value in a variable with =", "Show a result with print()"], "duration_seconds": 2100, "content_version": 2})
    nomedia = {"media_provider": None, "media_url": None, "media_asset_key": None, "duration_seconds": None}
    patch(c, "lecture_segments", S("000000000108"), {"segment_type": "intro", "title": "What you will do today", **nomedia, "settings": {"body": gen.INTRO}})
    patch(c, "lecture_segments", S("000000000101"), {"segment_type": "reading", "title": "Set up Python", **nomedia, "settings": {"body": gen.SETUP}})
    patch(c, "lecture_segments", S("000000000103"), {"segment_type": "reading", "title": "Notebooks and cells", **nomedia, "settings": {"body": gen.NOTEBOOKS}})
    patch(c, "lecture_segments", S("000000000105"), {"segment_type": "example", "title": "Variables and print()", **nomedia, "settings": {"body": gen.FIRST, "on_end": {"type": "open_exercise", "exercise_id": S("0000000000e1")}}})
    for sid, title in (("000000000102", "Check: Python setup"), ("000000000104", "Check: notebooks"), ("000000000106", "Lab: print your name"), ("000000000107", "Exit check")):
        patch(c, "lecture_segments", S(sid), {"title": title})
    patch(c, "mcq_questions", S("0000000000a1"), {"prompt": "Which command prints the version of Python installed on your computer?", "options": opts(("a", "python -v"), ("b", "python --version"), ("c", "python --check")), "correct_option_id": "b",
          "explanation_correct": "`python --version` prints the installed version. On macOS and Linux you may need `python3 --version`.", "explanation_incorrect": "Not quite. `python -v` turns on verbose mode, which traces every import. The command that prints the version is `python --version`.", "shuffle_options": False})
    patch(c, "mcq_questions", S("0000000000a2"), {"prompt": "Which statement about notebook cells is true?", "options": opts(("a", "Each cell can be run on its own, and all cells share the same variables while the kernel is running"), ("b", "Every cell has its own separate set of variables"), ("c", "Cells run automatically from top to bottom whenever you open the notebook")), "correct_option_id": "a",
          "explanation_correct": "Cells share one kernel, so a variable created in one cell can be used by any cell you run afterwards.", "explanation_incorrect": "Not quite. Cells are separate to run but share the same kernel, so variables carry over. You choose when each cell runs.", "shuffle_options": True})
    patch(c, "mcq_questions", S("0000000000a3"), {"prompt": "After running `price = 20` and then `price = price + 5`, what does `print(price)` show?", "options": opts(("a", "25"), ("b", "20"), ("c", "price + 5")), "correct_option_id": "a",
          "explanation_correct": "Python works out the right side first using the old value (20 + 5), then stores 25 back under `price`.", "explanation_incorrect": "Not quite. The second line reads the old value of `price`, adds 5, and stores the answer back, so `price` is now 25.", "shuffle_options": False})
    patch(c, "lecture_exercises", S("0000000000e1"), {"title": "Print your name", "instructions": "Create a variable named student_name that holds your name as text. Then print it so your name appears in the output.", "objective": "Store text in a variable and show it on screen with print()."})
    patch(c, "exercise_tests", S("0000000000f2"), {"remediation_segment_id": S("000000000105")})
print("done")
