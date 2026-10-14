# Environments and test accounts

## Environments (2026-10-14)
| Environment | Database | API / site | Status |
|---|---|---|---|
| Production / pilot | Supabase `ddiwlgbllhwcdykqjfne` (Tokyo) | Vercel `neuromind-lab-api` / `neuromind-lab` | live |
| Staging | **none** | none | **Not created.** The Supabase free plan allows 2 active projects per owner and the owner is already at that limit (the second slot is held by the paused project "BARCODE SCANNER APP", which was not touched). Options: pause or delete a project, or upgrade the plan (a paid decision for the owner). |

Until staging exists: run migrations and risky changes first on a local PostgreSQL with `scripts/dr_rehearsal.sh` (applies every migration from empty and restores a backup), take a backup with `scripts/backup_db.py` before touching production, and use Vercel preview deployments (they share the production database, so previews must not be used for destructive tests).

## Test accounts
- On 2026-10-14 all 44 synthetic accounts (`*@neuromind.test`, including the teacher) were deleted from the production database; their learner rows were removed by cascade. A backup was taken first (`private/backups`, git-ignored). Sign-in with the old default password was verified to fail.
- The old default password remains in public Git history. It protects nothing now. `scripts/check_secrets.py` blocks it from coming back.
- When tests need accounts (E2E, load test): create them with `DEV_USER_PASSWORD=<new strong password> scripts/create_dev_users.py` and `scripts/create_load_users.py`, run the tests, then delete them again (same admin API call used on 2026-10-14). Never reuse a password between runs that has appeared in chat or Git.
- Real administrator: run `ADMIN_EMAIL=you@example.com backend/.venv/bin/python scripts/create_admin.py` yourself (it asks for the password; nothing is stored). Until you do, nobody can use the teacher or admin screens.
- 3,325 synthetic audit-log rows remain (actor links removed by the cascade). They contain no personal data; they were kept because deleting audit records is itself something to avoid.

## Decisions 2026-10-14 (owner)
- **Staging:** the owner asked for a second Supabase project, and if that failed, to run on the single project only. Creation was attempted three times (once after the owner deleted another project) and Supabase refused each time: the free-plan limit of 2 active projects still counts a project outside the organisation visible to this tooling. **Decision in force: single project (production/pilot) only.** Safeguards stay as listed above: backup before changes, local migration rehearsal, no destructive tests on previews, test accounts deleted after each test run.
- **Real administrator:** `hussainsingapuri24@gmail.com` created with role admin. The password was supplied in chat and is short (8 characters); change it after first sign-in.
- **Supabase key rotation:** the owner decided to leave it ("let it be"). The service-role key shared early in the project stays active. This is an accepted risk, recorded here, with the runbook (`KEY_ROTATION_RUNBOOK.md`) ready if the decision changes.
