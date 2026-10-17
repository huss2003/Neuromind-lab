#!/usr/bin/env bash
# Update the worker to a newer commit: sudo REF=<branch/tag/commit> bash /opt/neuromind/infra/selfhost/update.sh
# Jobs are not lost: the service stops cleanly (current job finished or handed back), the queue waits in the database.
set -euo pipefail
APP=/opt/neuromind
REF="${REF:-claude/determined-bardeen-ip8pup}"
[ "$(id -u)" = 0 ] || { echo "run as root" >&2; exit 1; }
git -C "$APP" fetch -q --depth 1 origin "$REF" && git -C "$APP" checkout -q --force FETCH_HEAD
docker build -q -t neuromind-grader-sandbox "$APP/grader" >/dev/null
"$APP/venv/bin/pip" install -q -r "$APP/grader/requirements-worker.txt"
systemctl restart neuromind-worker
bash "$APP/infra/selfhost/verify.sh"
