# Backup, restore and rollback runbook

Rehearsed 2026-10-13 against the live dev project. What was and was not proved is stated at the end.

## What is backed up
| Data | How | Where |
|---|---|---|
| Application data (all 19 public tables: content, enrolments, sessions, attempts, submissions, drafts, audit log) | `scripts/backup_db.py` (service role, read only, REST) | `private/backups/<UTC>.json`, mode 600, git-ignored (contains learner data and hidden tests). Copy off the machine to storage you control. |
| Supabase Auth users (emails, password hashes) | **Not** in the JSON. Use the Supabase dashboard backup / project export, or re-invite users. | Supabase |
| Code and migrations | Git (`huss2003/Neuromind-lab`) | GitHub |
| Hidden tests | `private/exercise_tests*.json` (git-ignored) and the `exercise_tests` table | owner's secure storage |
| Secrets | Vercel env vars, AWS SSM Parameter Store | never in Git |

Cadence: before every production release and at least weekly. The free Supabase tier has no point-in-time recovery; the project owner decides whether to pay for it (not enabled, no spend approved).

## Restore into a new database
1. Create an empty Postgres/Supabase project (Auth enabled).
2. Apply `database/migrations/0001…000N` in order.
3. Recreate auth users (same UUIDs as `profiles.id`) so profile foreign keys hold.
4. Load each table from the JSON with triggers off (`session_replication_role = replica`), then re-enable.
5. Compare row counts with the backup (the rehearsal script does this).
6. Point `SUPABASE_URL` / keys of the API at the new project, redeploy, run `scripts/staging_drills.py` and the smoke E2E.

## Rehearsal
`scripts/dr_rehearsal.sh private/backups/<file>.json` starts a throw-away local PostgreSQL 16, stubs the Supabase roles/`auth` schema, applies all migrations from an empty database, restores the backup and compares per-table row counts.
Result on 2026-10-13: migrations 0001–0006 applied from zero; **19/19 tables restored with identical row counts** (3,334 rows).

## Rollback
- **Frontend / API:** each Vercel deployment is immutable. Roll back by re-assigning the production aliases (`neuromind-lab.vercel.app`, `neuromind-lab-api.vercel.app`) to the previous READY deployment (Vercel dashboard → Deployments → Promote, or the `assign_alias` API). No data change.
- **Database migration:** migrations are forward-only. Before applying one in production take a backup; if it must be undone, write a new numbered migration that reverses it (never edit an applied one).
- **Worker:** `systemctl stop neuromind-worker` makes the API leave submissions queued (they expire after `QUEUE_STALE_SECONDS`); switching `GRADER_MODE=inline` is not allowed in production (the sandbox is not available in the API process).

## What the rehearsal did not prove
- Supabase Auth user restore (not exported by the script).
- Row-level security policies on the restored copy (the stub roles exist; policies were applied by the migrations but not exercised against the restored data).
- Recovery time on the real hosted database; the local restore of 3.3k rows took seconds.
