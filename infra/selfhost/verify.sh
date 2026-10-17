#!/usr/bin/env bash
# Proves THIS machine's sandbox: isolation tests (network, files, secrets, limits, escapes), every lab's reference solution graded
# inside the real container, and the worker service health. Safe to run any time: sudo bash /opt/neuromind/infra/selfhost/verify.sh
set -uo pipefail
APP=/opt/neuromind
. /etc/neuromind/worker.env 2>/dev/null || true
export GRADER_RUNTIME="${GRADER_RUNTIME:-runsc}"
FAIL=0
"$APP/venv/bin/pip" install -q -r "$APP/grader/requirements-verify.txt" >/dev/null
echo "== 1. runtime: $GRADER_RUNTIME"
docker run --rm --runtime="$GRADER_RUNTIME" --network none neuromind-grader-sandbox python -c "print('sandbox starts')" || FAIL=1
if [ "$GRADER_RUNTIME" = runsc ]; then
  docker run --rm --runtime=runsc --network none neuromind-grader-sandbox python -c "import platform; print('kernel seen by learner code:', platform.release())"
fi
echo "== 2. isolation and grading tests in the real sandbox"
( cd "$APP/grader" && sudo -u nmworker --preserve-env=GRADER_RUNTIME env PYTHONPATH="$APP/grader" PYTHONDONTWRITEBYTECODE=1 \
    "$APP/venv/bin/python" -m pytest -q -p no:cacheprovider tests -rs ) || FAIL=1
echo "== 3. every lab solution graded inside the sandbox (hidden checks live elsewhere: PARTIAL is expected)"
( cd "$APP" && sudo -u nmworker --preserve-env=GRADER_RUNTIME env PYTHONDONTWRITEBYTECODE=1 \
    "$APP/venv/bin/python" scripts/verify_labs.py content/lectures --sandbox --tests "$APP/infra/selfhost/no-hidden-tests.json" | tail -3 ) || FAIL=1
echo "== 4. worker service"
systemctl is-active --quiet neuromind-worker && echo "neuromind-worker: active" || { echo "neuromind-worker: NOT active"; FAIL=1; }
journalctl -u neuromind-worker -n 5 --no-pager -o cat | grep -E "sandbox ready|WARNING|Error" || true
[ "$FAIL" = 0 ] && echo "ALL CHECKS PASSED" || { echo "SOME CHECKS FAILED"; exit 1; }
