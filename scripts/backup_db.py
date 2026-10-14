"""Logical backup of every public table through the Supabase REST API (service role, read only).
  backend/.venv/bin/python scripts/backup_db.py [out.json]
Output defaults to private/backups/<UTC timestamp>.json (git-ignored: it contains learner data and hidden tests).
Does NOT include Supabase Auth users (emails/password hashes); see docs/06-operations/BACKUP_RESTORE_RUNBOOK.md."""
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
BASE, KEY = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1", os.environ["SUPABASE_SERVICE_ROLE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}


def tables() -> list[str]:
    spec = httpx.get(f"{BASE}/", headers=H, timeout=30).json()
    return sorted(p.strip("/") for p in spec["paths"] if p != "/" and not p.startswith("/rpc/"))


def dump(table: str) -> list[dict]:
    rows: list[dict] = []
    while True:
        r = httpx.get(f"{BASE}/{table}", headers={**H, "Range": f"{len(rows)}-{len(rows) + 999}"}, params={"select": "*"}, timeout=60)
        r.raise_for_status()
        page = r.json()
        rows += page
        if len(page) < 1000:
            return rows


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "private" / "backups" / f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {t: dump(t) for t in tables()}
    out.write_text(json.dumps({"taken_at": datetime.now(UTC).isoformat(), "tables": data}, default=str))
    out.chmod(0o600)
    print(f"backup written: {out} ({sum(map(len, data.values()))} rows in {len(data)} tables)")
    for t, rows in data.items():
        print(f"  {t:32s} {len(rows)}")
