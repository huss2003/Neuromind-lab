"""Lightweight secret/credential scan of tracked files. Exit 1 on a finding. Run in CI and before pushing.
Not a replacement for a full scanner (CI also runs gitleaks); it catches the mistakes this project has actually made."""
import re
import subprocess
import sys

PATTERNS = {
    "JWT-looking token": re.compile(r"eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}"),
    "AWS access key id": re.compile(r"\b(AKIA|ASIA)[A-Z0-9]{16}\b"),
    "private key block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "known leaked dev password": re.compile(r"NeuroMind-dev-2026"),
    "service role assigned a value": re.compile(r"SERVICE_ROLE_KEY[ \t]*=[ \t]*[A-Za-z0-9._-]{20,}"),
}
ALLOW_PATHS = ("docs/09-audit/", "scripts/create_dev_users.py", "scripts/check_secrets.py")  # audit reports may NAME the leaked default password (never a real secret)
SKIP_SUFFIX = (".png", ".jpg", ".ico", ".lock", ".svg")


def main() -> int:
    files = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout.split()
    bad = 0
    for f in files:
        if f.endswith(SKIP_SUFFIX):
            continue
        try:
            text = open(f, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        for name, rx in PATTERNS.items():
            if name == "known leaked dev password" and f.startswith(ALLOW_PATHS):
                continue
            for m in rx.finditer(text):
                if re.search(r"replace|your|example|changeme|xxx|<", m.group(0), re.I):
                    continue  # documented placeholder
                line = text.count("\n", 0, m.start()) + 1
                print(f"{f}:{line}: {name}")  # location only, never the value
                bad += 1
    print("secret scan:", "FAILED" if bad else "clean", f"({len(files)} files)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
