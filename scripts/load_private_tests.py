"""Load hidden exercise-test definitions from a PRIVATE file that is never committed.

  private/exercise_tests.json  ->  {"<exercise_tests.id>": {<definition json>}, ...}

Usage (repo root):  backend/.venv/bin/python scripts/load_private_tests.py
Needs SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the environment/.env. Definitions are never printed."""
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
SRC = Path(os.getenv("PRIVATE_TESTS_FILE", ROOT / "private" / "exercise_tests.json"))
if not SRC.exists():
    sys.exit(f"{SRC} not found. Create it locally (it is git-ignored); see docs/06-operations/E2E_LEARNER_JOURNEY.md.")
URL, KEY = os.environ["SUPABASE_URL"].rstrip("/"), os.environ["SUPABASE_SERVICE_ROLE_KEY"]
H = {"apikey": KEY, **({} if KEY.startswith("sb_secret_") else {"Authorization": f"Bearer {KEY}"}), "Content-Type": "application/json"}
defs = json.loads(SRC.read_text())
with httpx.Client(timeout=15) as c:
    for test_id, definition in defs.items():
        r = c.patch(f"{URL}/rest/v1/exercise_tests", headers=H, params={"id": f"eq.{test_id}"}, json={"definition": definition})
        r.raise_for_status()
        print(f"updated test {test_id[-4:]}")
