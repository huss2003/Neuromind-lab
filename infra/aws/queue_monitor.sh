#!/usr/bin/env bash
# Runs every minute on the worker host (systemd timer). Publishes two CloudWatch metrics:
#   NeuroMind/Grading WorkerActive (1 = the worker service is running)  and  OldestQueuedSeconds (age of the oldest waiting job).
# Needs the instance role to allow cloudwatch:PutMetricData. Reads the API URL and worker token from /etc/neuromind/worker.env.
set -uo pipefail
set -a; . /etc/neuromind/worker.env; set +a
REGION="${AWS_REGION:-ap-southeast-2}"
active=0; systemctl is-active --quiet neuromind-worker && active=1
age=0
body="$(curl -fsS -m 10 -H "X-Worker-Token: $GRADER_WORKER_TOKEN" "$API_BASE_URL/api/v1/internal/grader/health" 2>/dev/null || true)"
if [ -n "$body" ]; then
  a="$(printf '%s' "$body" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("oldest_queued_seconds") or 0)' 2>/dev/null || echo 0)"
  age="${a:-0}"
else
  age=-1   # API unreachable: reported as -1 so the alarm on "missing or bad data" can fire separately
fi
aws cloudwatch put-metric-data --region "$REGION" --namespace NeuroMind/Grading \
  --metric-data "MetricName=WorkerActive,Value=$active,Unit=Count" "MetricName=OldestQueuedSeconds,Value=$age,Unit=Seconds" >/dev/null
