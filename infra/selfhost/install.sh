#!/usr/bin/env bash
# NeuroMind self-hosted grading worker. Portable: the same script installs it on any Ubuntu 22.04/24.04 or Debian 12 machine,
# virtual machine or rented server (x86-64 or ARM64). Run as root ON A MACHINE THAT HOLDS NOTHING ELSE (see
# docs/06-operations/SELF_HOSTED_GRADER.md): the worker account can start containers, which is equivalent to control of this machine.
#
#   sudo bash install.sh            # asks for the API address and the worker token (hidden); nothing is printed or logged
# Options (environment): REF=<git branch/tag/commit>  GRADER_RUNTIME=runsc|runc (default runsc = gVisor)  WORKER_CONCURRENCY=2
set -euo pipefail
REPO="${REPO:-https://github.com/huss2003/Neuromind-lab.git}"
REF="${REF:-claude/determined-bardeen-ip8pup}"
APP=/opt/neuromind
RUNTIME="${GRADER_RUNTIME:-runsc}"
CONCURRENCY="${WORKER_CONCURRENCY:-2}"
die() { echo "ERROR: $*" >&2; exit 1; }
[ "$(id -u)" = 0 ] || die "run as root: sudo bash install.sh"
case "$RUNTIME" in runsc|runc) ;; *) die "GRADER_RUNTIME must be runsc or runc";; esac
[ "$RUNTIME" = runc ] && echo "WARNING: GRADER_RUNTIME=runc uses plain Docker isolation (no gVisor). Not recommended."

# 1. Refuse an unsafe host. Inside WSL the Windows drives (C:) are mounted and Windows programs can be started from Linux by
#    default; a sandbox escape would then reach the owner's personal files. Require both to be switched off.
if grep -qi microsoft /proc/version 2>/dev/null; then
  grep -qiE '^\s*enabled\s*=\s*false' /etc/wsl.conf 2>/dev/null && grep -qiE '^\s*\[interop\]' /etc/wsl.conf 2>/dev/null \
    || die "WSL detected. Use a separate virtual machine instead (recommended), or copy infra/selfhost/wsl.conf to /etc/wsl.conf, run 'wsl --shutdown' in Windows and start again."
  [ -z "$(ls /mnt/c 2>/dev/null)" ] || die "the Windows C: drive is still visible at /mnt/c; apply wsl.conf and restart WSL"
fi

# 2. Packages: Docker, git, Python for the worker, a firewall and automatic security updates.
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q ca-certificates curl gnupg git python3 python3-venv docker.io ufw unattended-upgrades
systemctl enable --now docker

# 3. gVisor (runsc): a user-space kernel between learner code and this machine's kernel.
if [ "$RUNTIME" = runsc ] && ! command -v runsc >/dev/null; then
  curl -fsSL https://gvisor.dev/archive.key | gpg --dearmor --yes -o /usr/share/keyrings/gvisor-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main" \
    > /etc/apt/sources.list.d/gvisor.list
  apt-get update -q && apt-get install -y -q runsc
fi
if [ "$RUNTIME" = runsc ]; then runsc install && systemctl restart docker; fi

# 4. A dedicated account with no login shell. Learner code never runs as this account: it runs as nobody inside the sandbox.
id -u nmworker >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin nmworker
usermod -aG docker nmworker

# 5. Code, sandbox image (pinned runtime) and the worker's own Python environment.
if [ -d "$APP/.git" ]; then git -C "$APP" fetch --depth 1 origin "$REF" && git -C "$APP" checkout -q --force FETCH_HEAD
else rm -rf "$APP" && git clone -q --depth 1 --branch "$REF" "$REPO" "$APP"; fi
docker build -q -t neuromind-grader-sandbox "$APP/grader" >/dev/null
python3 -m venv "$APP/venv"
"$APP/venv/bin/pip" install -q -r "$APP/grader/requirements-worker.txt"

# 6. Configuration: root-only file; the token is read without echo and never printed.
install -d -m 700 /etc/neuromind
if [ ! -f /etc/neuromind/worker.env ]; then
  read -r -p "API address (e.g. https://neuromind-lab-api.vercel.app): " API_BASE_URL
  read -r -s -p "Worker token (input hidden): " GRADER_WORKER_TOKEN; echo
  [ -n "$API_BASE_URL" ] && [ -n "$GRADER_WORKER_TOKEN" ] || die "both values are required"
  ( umask 077; cat > /etc/neuromind/worker.env <<ENV
API_BASE_URL=$API_BASE_URL
GRADER_WORKER_TOKEN=$GRADER_WORKER_TOKEN
GRADER_RUNTIME=$RUNTIME
WORKER_CONCURRENCY=$CONCURRENCY
GRADING_TIMEOUT_SECONDS=5
GRADING_MEMORY_MB=128
ENV
  )
fi

# 7. The service: restarts on failure, starts at boot, no extra privileges, read-only view of the system.
cat > /etc/systemd/system/neuromind-worker.service <<'UNIT'
[Unit]
Description=NeuroMind grading worker
After=network-online.target docker.service
Wants=network-online.target
Requires=docker.service
[Service]
User=nmworker
WorkingDirectory=/opt/neuromind/grader
EnvironmentFile=/etc/neuromind/worker.env
Environment=PYTHONPATH=/opt/neuromind/grader PYTHONDONTWRITEBYTECODE=1 DOCKER_CONFIG=/tmp/docker
ExecStart=/opt/neuromind/venv/bin/python worker.py
Restart=always
RestartSec=10
KillSignal=SIGTERM
TimeoutStopSec=45
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
LockPersonality=true
[Install]
WantedBy=multi-user.target
UNIT

# 8. Firewall: nothing may connect in (the worker only calls out). SSH stays reachable if it is installed.
ufw default deny incoming >/dev/null && ufw default allow outgoing >/dev/null
if [ -f /usr/sbin/sshd ]; then ufw allow OpenSSH >/dev/null; fi
ufw --force enable >/dev/null
dpkg-reconfigure -f noninteractive unattended-upgrades >/dev/null 2>&1 || true

systemctl daemon-reload
systemctl enable --now neuromind-worker
echo "Installed. Running the isolation and lab checks against this machine's real sandbox..."
bash "$APP/infra/selfhost/verify.sh"
