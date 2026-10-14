"""Create the first real administrator. Run by the OWNER on their own machine; the password is typed, never stored or logged.
  ADMIN_EMAIL=you@example.com backend/.venv/bin/python scripts/create_admin.py
Needs SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env (server-side only). Refuses weak passwords."""
import getpass
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
URL, KEY = os.environ["SUPABASE_URL"].rstrip("/"), os.environ["SUPABASE_SERVICE_ROLE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
if "@" not in email or email.endswith("@neuromind.test"):
    sys.exit("Set ADMIN_EMAIL to a real address (not @neuromind.test).")
pw = getpass.getpass("Choose a password (14+ characters): ")
if len(pw) < 14 or pw != getpass.getpass("Repeat it: "):
    sys.exit("Password too short or the two entries differ.")
r = httpx.post(f"{URL}/auth/v1/admin/users", headers=H, timeout=30,
               json={"email": email, "password": pw, "email_confirm": True, "user_metadata": {"display_name": "Administrator"}})
if r.status_code >= 300:
    sys.exit(f"Could not create the user: HTTP {r.status_code}")
uid = r.json()["id"]
p = httpx.patch(f"{URL}/rest/v1/profiles?id=eq.{uid}", headers={**H, "Prefer": "return=minimal"}, timeout=30,
                json={"role": "admin", "display_name": "Administrator"})
sys.exit(0 if p.status_code < 300 else f"User created but role update failed: HTTP {p.status_code}")
