#!/usr/bin/env bash
# Starts API (:8000), grader (:8010, 127.0.0.1 only) and frontend (:5173). Run from repo root after setup (see README).
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
trap 'kill 0' EXIT
(cd backend && .venv/bin/uvicorn app.main:app --port 8000 --reload) &
if command -v docker >/dev/null && docker info >/dev/null 2>&1; then
  docker image inspect neuromind-grader-sandbox >/dev/null 2>&1 || docker build -t neuromind-grader-sandbox grader/
  (cd grader && ../backend/.venv/bin/uvicorn grader_service.app:app --host 127.0.0.1 --port 8010) &
else
  echo "WARNING: Docker not running. Official grading will report 'grader unavailable' (never a learner failure)."
fi
(cd frontend && VITE_API_BASE_URL=http://localhost:8000 pnpm dev --host 127.0.0.1) &
wait
