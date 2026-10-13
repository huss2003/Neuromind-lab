# NeuroMind AI Learning Lab — Pre-Vibe-Coding Pack
Status: planning baseline, 2026-10-13. Audience: solo developer using AI coding tools.

## Read in order
1. PRD; 2. User stories and acceptance criteria; 3. Architecture/stack; 4. Data model; 5. API spec; 6. CLAUDE.md / AGENTS.md; 7. User flows; 8. Design system; 9. Wireframes; 10. Security; 11. Test plan; 12. NFRs; 13. Error handling; 14. Environment; 15. Deployment; 16. Implementation plan; 17. PROGRESS; 18. ADRs; 19. Glossary; 20. Reference patterns; 21. Prompt library.

## Scope baseline
Build one data-driven sample lecture first (recommended Lecture 9: Python setup, notebooks and the first program). It must sequence separate video segments, two MCQ checkpoints, results/explanations, a practical video, automatic exercise opening, Pyodide browser practice, official local Docker grading, retry/remediation, progress persistence, and a basic teacher result view. The full course has 104 lectures, but do not build 104 bespoke pages or record all videos before the sample flow works.

## Constraints and cautions
- Solo developer; use free plans/local tools and existing AI subscription. No paid service/API without approval.
- Frontend: React/TypeScript; Cloudflare Pages Free. API: FastAPI local or Render Free. Auth/database: Supabase Free. Browser practice: Pyodide. Official grading: separate local Docker worker.
- Google Drive can store master recordings and may be tested for playback. Use HTML5-compatible media events for reliable automatic transitions; test Cloudflare R2 for sample playback.
- Never expose Docker, Docker socket, or local grader to public internet.
- Free prototype is not a production-secure code runner or proof of 100 concurrent grading jobs.
- Version pins are a proposed baseline and must be verified together before install.
- Keep `.env`, secrets, answer keys and hidden tests out of Git/client responses.

## Prototype acceptance gate
Learner can sign in; play segments; answer two MCQs and see server-calculated results; see practical video; have exercise open automatically; run supported Python in browser; submit to a local isolated grader; receive result/retry; refresh and resume; and have results visible to authorised teacher.

## Change control
For any scope/schema/API/security/cost decision: update the relevant spec, tests, ADR if needed, and PROGRESS.md before or with implementation. Do not silently infer major requirements.

---
# Running locally (verified steps are marked; see PROGRESS.md for what has NOT been verified)

## Prerequisites
Node 22, pnpm (10.x tested), Python 3.12+ (3.13 tested), Docker (only for official grading), a Supabase DEV project.

## One-time setup
```bash
cp .env.example .env            # then fill SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY,
                                # VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY, GRADER_SHARED_SECRET
python3 -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements.txt
(cd frontend && pnpm install --frozen-lockfile)
# Database: apply database/migrations/*.sql in order, then database/seed/001_lecture9_sample.sql (SQL editor or Supabase CLI)
CONFIRM_DEV_PROJECT=yes backend/.venv/bin/python scripts/create_dev_users.py   # learner1/2/3 + teacher @neuromind.test
docker build -t neuromind-grader-sandbox grader/                               # official-grading sandbox image
```
Never commit `.env`. The service-role key is server-only (API); the browser only gets the anon/publishable key.

## Run
```bash
scripts/dev.sh      # API :8000, grader 127.0.0.1:8010 (needs Docker), frontend http://127.0.0.1:5173
```
Sign in as `learner1@neuromind.test` (password printed by the user script) and open Lecture 9. Teacher: `teacher@neuromind.test` -> Results.

## Checks
```bash
cd backend && .venv/bin/ruff check . && .venv/bin/pytest -q          # API + business rules (in-memory repo)
cd grader  && ../backend/.venv/bin/pytest -q                          # grader logic (Docker test auto-skips without Docker)
cd frontend && pnpm lint && pnpm typecheck && pnpm test && pnpm build
cd frontend && pnpm exec playwright test smoke                        # boots the app in a real browser (no backend needed)
cd frontend && pnpm e2e                                               # full journeys A-E: needs the whole stack + users + Docker
```

## Deploying the frontend to Vercel (not yet done)
1. Vercel -> Add New Project -> import this repo, set **Root Directory = `frontend`** (config in `frontend/vercel.json`).
2. Environment variables (public values only): `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_BASE_URL` (URL of the hosted API).
3. The API (`backend/`) is a separate FastAPI service (docs plan Render Free); set its `CORS_ALLOWED_ORIGINS` to the Vercel URL and keep `SUPABASE_SERVICE_ROLE_KEY` only there. In Supabase Auth settings add the Vercel URL to allowed redirect URLs.
4. The Docker grader stays local/private: a hosted preview will show "grader unavailable" for official grading (never a learner failure).
