"""Create confirmed DEV users via the Supabase Admin API (needs SUPABASE_SERVICE_ROLE_KEY in .env).
Run from the repo root:  backend/.venv/bin/python scripts/create_dev_users.py
Creates learner1/2/3 and teacher @neuromind.test with the password below. DEV PROJECTS ONLY."""
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
URL, KEY = os.environ["SUPABASE_URL"].rstrip("/"), os.environ["SUPABASE_SERVICE_ROLE_KEY"]
PASSWORD = os.getenv("DEV_USER_PASSWORD", "")
# No default: the old default was committed to a public repository and must be treated as compromised.
if len(PASSWORD) < 14 or PASSWORD == "NeuroMind-dev-2026!":
    sys.exit("Set DEV_USER_PASSWORD in your shell (not in Git) to a unique password of at least 14 characters.")
if os.getenv("APP_ENV", "development").lower() in {"production", "prod"}:
    sys.exit("Refusing to create development users when APP_ENV is production.")
USERS = [("learner1@neuromind.test", "Learner One", "learner"), ("learner2@neuromind.test", "Learner Two", "learner"),
         ("learner3@neuromind.test", "Learner Three", "learner"),
         ("teacher@neuromind.test", "Teacher", "teacher")]
H = {"apikey": KEY, **({} if KEY.startswith("sb_secret_") else {"Authorization": f"Bearer {KEY}"})}

if "localhost" not in URL and os.getenv("CONFIRM_DEV_PROJECT") != "yes":
    print(f"About to create test users in {URL}. Re-run with CONFIRM_DEV_PROJECT=yes if this is a DEV project.")
    sys.exit(1)

with httpx.Client(timeout=15) as c:
    for email, name, role in USERS:
        r = c.post(f"{URL}/auth/v1/admin/users", headers=H, json={
            "email": email, "password": PASSWORD, "email_confirm": True, "user_metadata": {"display_name": name}})
        if r.status_code in (200, 201):
            uid = r.json()["id"]
        elif r.status_code in (409, 422):  # already exists
            uid = next(u["id"] for u in c.get(f"{URL}/auth/v1/admin/users", headers=H, params={"per_page": 200}).json()["users"] if u["email"] == email)
        else:
            sys.exit(f"{email}: {r.status_code} {r.text[:200]}")
        c.patch(f"{URL}/rest/v1/profiles", headers=H, params={"id": f"eq.{uid}"}, json={"role": role, "display_name": name}).raise_for_status()
        print(f"ok  {email}  role={role}")
print("Done. Passwords were set from DEV_USER_PASSWORD (not printed).")
