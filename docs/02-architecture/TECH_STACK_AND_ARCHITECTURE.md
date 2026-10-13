# Tech Stack and Architecture
Version 0.1.0. Pins below are a proposed baseline, not a claim of newest versions. Verify compatibility and availability before install; commit lockfiles and update this document if changed.

## Proposed version baseline
- Node.js `22.x` LTS; pnpm `9.15.4`
- React `19.0.0`; TypeScript `5.7.3`; Vite `6.1.0`
- React Router `7.1.5`; TanStack Query `5.66.0`; Zod `3.24.2`
- `@monaco-editor/react` `4.6.0`; Pyodide `0.27.4`
- Python `3.12.x`; FastAPI `0.115.8`; Uvicorn `0.34.0`; Pydantic `2.10.6`
- `@supabase/supabase-js` `2.49.1`
- Vitest `3.0.5`; Testing Library React `16.1.0`; Playwright `1.50.1`
- pytest `8.3.4`; Ruff `0.9.7`; ESLint `9.19.0`; Prettier `3.5.0`
- PostgreSQL managed by Supabase; Docker Engine/Desktop current stable compatible with developer OS.
Before coding, verify package compatibility, pin exact runtime patches in `.nvmrc`/`.python-version`, install together, run tests, and commit lockfiles.

## Architecture diagram
```text
Browser: React + TS
  |-- Supabase Auth session
  |-- segmented HTML5 video player
  |-- MCQ UI / Monaco / Pyodide Web Worker (practice)
  |
  +--> Supabase Auth + PostgreSQL (durable content/progress/results)
  |
  +--> FastAPI API (local or Render Free preview)
          |-- token/role checks
          |-- lecture/checkpoint state transitions
          |-- server-side MCQ scoring
          |-- submissions/results
          |
          +--> local grading adapter --> isolated Docker worker
Video: Drive master/source assets; test R2/HTML5-compatible source for deterministic `ended` transitions.
```

## Responsibilities
**Frontend:** render states, play segments, show MCQs/results, run supported browser practice. Never decide official scores or permissions.
**API:** verify tokens, enforce ownership/roles, validate payloads, calculate MCQ score, validate state transitions, coordinate grading, persist results.
**Database:** durable content and learner records, FK/unique constraints, RLS where client access exists.
**Grader:** separate process/container; constrained, disposable, no secrets/network by default; returns structured result.
**Media:** provider adapter; no dependency on undocumented Drive iframe behaviour for critical flow.

## Authentication
Supabase Auth; API verifies token; identity comes from verified claims. Roles are trusted server-managed data. Service-role key is server-only.

## Execution modes
1. Pyodide in browser worker for compatible practice; terminate on timeout; label “practice — not official grade.”
2. Local Docker worker for official grade during development; run outside API process, no public exposure, resource limits, no Docker socket/host mounts/secrets/network.

## Prototype hosting
- Cloudflare Pages Free: static frontend.
- Render Free or local FastAPI: preview API; expect cold starts/limits.
- Supabase Free: Auth/Postgres, quota/pause constraints.
- Cloudflare R2: optional sample video assets within free allowance.
- GitHub: source control.
No provider combination guarantees 100 concurrent grading jobs.

## Future production
After approval: choose always-on API, isolated hosted worker pool, optional queue, video delivery, monitoring/backups, and perform load/security testing. Test 100 sessions separately from 10/25/50/100 simultaneous grading jobs.
