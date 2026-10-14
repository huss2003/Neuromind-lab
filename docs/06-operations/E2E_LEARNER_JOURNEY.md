# End-to-end learner journey (real stack)

**Status: NOT RUN.** This cloud container has no Docker daemon and cannot reach Supabase from the shell, so the journey below has only been exercised through the mocked-network browser suite (`pnpm test:ui`) and in-memory backend tests. Run this on a machine with Docker.

## Setup
1. A **dev** Supabase project, `.env` filled from `.env.example` (never commit it).
2. Apply `database/migrations/0001…0006` in order, then `database/seed/001…004`.
3. Create synthetic users: `export DEV_USER_PASSWORD='<a unique 14+ character password>'` then `CONFIRM_DEV_PROJECT=yes backend/.venv/bin/python scripts/create_dev_users.py`. There is no default password.
4. Load the private hidden test: create `private/exercise_tests.json` (git-ignored; format in `scripts/load_private_tests.py`), then `backend/.venv/bin/python scripts/load_private_tests.py`.
5. `docker build -t neuromind-grader-sandbox grader/`
6. Start everything: `scripts/dev.sh` (inline grading), or for the queue path set `GRADER_MODE=queue`, `GRADER_WORKER_TOKEN`, and run `API_BASE_URL=http://127.0.0.1:8000 GRADER_WORKER_TOKEN=… python grader/worker.py`.

## Run
`cd frontend && DEV_USER_PASSWORD=… pnpm e2e`

## Steps and expected outcomes
| # | Step | Expected (and what to verify in the database) |
|---|---|---|
| 1 | Sign in as learner1 | Dashboard shows Lecture 9; `profiles.role='learner'` |
| 2 | Open lecture, Start, intro Continue | `lecture_sessions` row created |
| 3 | Video 1 → MCQ 1 (answer wrong, then right) | two `checkpoint_attempts` rows; explanation shown |
| 4 | Video 2 → MCQ 2 | checkpoint completed server-side |
| 5 | Practical video → lab opens | exercise unlocked |
| 6 | Submit a wrong solution | `lab_submissions.status='failed'`, criteria and remediation shown, hidden test label generic |
| 7 | Replay the remediation section, retry with the correct code | `status='passed'`, `score=100` |
| 8 | Use one hint, submit again | that attempt's score is 10 points lower; the earlier best score is unchanged |
| 9 | Submit a worse answer after a pass | best valid score stays |
| 10 | Duplicate the submit (double click / same Idempotency-Key) | one row only |
| 11 | Finish the exit check, press Finish | `lecture_sessions.status='completed'`; survives refresh and sign-out/in |
| 12 | Stop the worker mid-job (queue mode) | job returns to `queued` after the lease expires and completes on restart |

## Cleanup
Delete only rows for the synthetic users. Never run it against a project with real learners.

## Troubleshooting
* "system error — not your fault": the grader or worker is not reachable, or Docker is not running. Nothing was marked incorrect.
* Stuck `running` rows: a worker died; they are re-claimed after 60 s and dead-lettered after 3 claims.
