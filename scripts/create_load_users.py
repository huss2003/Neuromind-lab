"""Create N synthetic load-test learners (loadtest01@neuromind.test ...) and enrol them in the sample course. DEV project only.
  DEV_USER_PASSWORD=... CONFIRM_DEV_PROJECT=yes backend/.venv/bin/python scripts/create_load_users.py 50"""
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
URL, KEY = os.environ["SUPABASE_URL"].rstrip("/"), os.environ["SUPABASE_SERVICE_ROLE_KEY"]
PASSWORD = os.getenv("DEV_USER_PASSWORD", "")
COURSE = "00000000-0000-4000-8000-000000000001"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 50
if len(PASSWORD) < 14 or os.getenv("CONFIRM_DEV_PROJECT") != "yes":
    sys.exit("Set DEV_USER_PASSWORD (14+ chars) and CONFIRM_DEV_PROJECT=yes. DEV projects only.")
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
with httpx.Client(timeout=30) as c:
    for i in range(1, N + 1):
        email = f"loadtest{i:02d}@neuromind.test"
        r = c.post(f"{URL}/auth/v1/admin/users", headers=H, json={"email": email, "password": PASSWORD, "email_confirm": True,
                                                                  "user_metadata": {"display_name": f"Load Test {i:02d}"}})
        if r.status_code in (200, 201):
            uid = r.json()["id"]
        elif r.status_code in (409, 422):
            users = c.get(f"{URL}/auth/v1/admin/users", headers=H, params={"per_page": 200}).json()["users"]
            uid = next(u["id"] for u in users if u["email"] == email)
        else:
            sys.exit(f"{email}: {r.status_code}")
        e = c.post(f"{URL}/rest/v1/enrollments", headers={**H, "Content-Type": "application/json", "Prefer": "resolution=ignore-duplicates"},
                   json={"learner_id": uid, "course_id": COURSE}, params={"on_conflict": "learner_id,course_id"})
        if e.status_code not in (200, 201, 204, 409):
            sys.exit(f"enrol {email}: {e.status_code} {e.text[:100]}")
    print(f"ok: {N} synthetic learners ready")
