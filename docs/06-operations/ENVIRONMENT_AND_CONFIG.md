# Environment and Configuration

## Local prerequisites
Git; Node 22.x; pnpm 9.15.4; Python 3.12.x; Docker Desktop/Engine; editor; GitHub; Supabase project; Cloudflare account for Pages/R2; Render account only if remote preview is needed. Verify exact runtime patches and write `.nvmrc`/`.python-version` after setup.

## `.env.example` names
```dotenv
APP_ENV=development
APP_NAME=neuromind-lab
LOG_LEVEL=INFO
FRONTEND_ORIGIN=http://localhost:5173
API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
CORS_ALLOWED_ORIGINS=http://localhost:5173
MAX_SOURCE_CODE_BYTES=50000
MAX_OUTPUT_BYTES=20000
GRADING_TIMEOUT_SECONDS=5
GRADING_MEMORY_MB=128
GRADING_CPU_LIMIT=1
GRADING_NETWORK_ENABLED=false
GRADER_MODE=local_docker
GRADER_SHARED_SECRET=
GRADER_BASE_URL=http://127.0.0.1:8010
R2_PUBLIC_BASE_URL=
R2_BUCKET_NAME=
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
DRIVE_EMBED_ALLOWED=false
SENTRY_DSN=
```
Only names/defaults belong here. `VITE_*` variables are public; never put secrets in them. Remove unused variables from actual implementation.

## Local setup workflow
1. Clone repository.
2. Install pinned Node/Python versions.
3. Install frontend from lockfile (`pnpm install --frozen-lockfile`).
4. Create Python virtual environment and install locked backend requirements.
5. Copy `.env.example` to `.env`; fill development-only values.
6. Apply SQL migrations to development project.
7. Run idempotent demo seed.
8. Start API and frontend.
9. Start local grader only when Docker is available and explicitly enabled.
10. Run tests and verify health endpoint/lecture flow.
Actual commands must be verified and documented in root README after repository structure exists.

## Environment separation
Local: synthetic data and local grader. Preview: Pages + Render Free if desired, dev Supabase, demo media; grader remains local-only. Production: separate project/secrets, approved host, isolated hosted worker, backups/monitoring and load/security tests.

## Free-plan checklist
Check cold start, quotas, project pause, media CORS/range requests, billing settings, alerts/limits, no paid service enabled, and local fallback before demo.
