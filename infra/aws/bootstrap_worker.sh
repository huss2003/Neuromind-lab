#!/usr/bin/env bash
# Run ONCE on a fresh Amazon Linux 2023 instance as root:  sudo bash bootstrap_worker.sh
# Installs Docker + Python, fetches the repo, builds the sandbox image and installs the worker as a systemd service.
# It never prints or stores the worker token anywhere except /etc/neuromind/worker.env (root-only, mode 600).
set -euo pipefail
REPO="${REPO:-https://github.com/huss2003/Neuromind-lab.git}"
REF="${REF:-claude/determined-bardeen-ip8pup}"
APP=/opt/neuromind

dnf install -y docker git python3.12 python3.12-pip
systemctl enable --now docker

id -u nmworker >/dev/null 2>&1 || useradd --system --create-home --shell /sbin/nologin nmworker
usermod -aG docker nmworker   # the worker needs the Docker socket; this host must hold no other secrets

rm -rf "$APP" && git clone --depth 1 --branch "$REF" "$REPO" "$APP"
docker build -t neuromind-grader-sandbox "$APP/grader"
python3.12 -m venv "$APP/venv"
"$APP/venv/bin/pip" install --quiet httpx==0.28.1 pydantic==2.10.6 fastapi==0.115.8

install -d -m 700 /etc/neuromind
if [ ! -f /etc/neuromind/worker.env ]; then
  umask 077
  if [ -n "${TOKEN_SSM_PARAM:-}" ]; then   # non-interactive: token lives in SSM Parameter Store (SecureString), never in user-data
    : "${API_BASE_URL:?set API_BASE_URL}"
    GRADER_WORKER_TOKEN="$(aws ssm get-parameter --name "$TOKEN_SSM_PARAM" --with-decryption --region "${AWS_REGION:-ap-southeast-2}" --query Parameter.Value --output text)"
  else
    read -r -p "API base URL (e.g. https://neuromind-lab-api.vercel.app): " API_BASE_URL
    read -r -s -p "Worker token (input hidden): " GRADER_WORKER_TOKEN; echo
  fi
  cat > /etc/neuromind/worker.env <<EOF
API_BASE_URL=$API_BASE_URL
GRADER_WORKER_TOKEN=$GRADER_WORKER_TOKEN
WORKER_CONCURRENCY=1
GRADING_TIMEOUT_SECONDS=5
GRADING_MEMORY_MB=128
EOF
fi

cat > /etc/systemd/system/neuromind-worker.service <<'EOF'
[Unit]
Description=NeuroMind grading worker
After=network-online.target docker.service
Wants=network-online.target

[Service]
User=nmworker
WorkingDirectory=/opt/neuromind/grader
EnvironmentFile=/etc/neuromind/worker.env
Environment=PYTHONPATH=/opt/neuromind/grader
ExecStart=/opt/neuromind/venv/bin/python worker.py
Restart=always
RestartSec=5
KillSignal=SIGTERM
TimeoutStopSec=30
NoNewPrivileges=true
ProtectHome=true

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now neuromind-worker
systemctl --no-pager status neuromind-worker | head -5
