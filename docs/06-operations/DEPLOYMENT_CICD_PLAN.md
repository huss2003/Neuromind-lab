# Deployment and CI/CD Plan

## Environments
- Local: frontend/API locally, development Supabase, local Docker grader, synthetic data.
- Preview/demo: Cloudflare Pages preview; optional Render Free API; development Supabase; non-sensitive demo media; local grader not exposed publicly.
- Production later: separate resources/secrets, approved host, isolated hosted grading, backups, monitoring, security/load testing.

## Branching
`main` is tested baseline. Use `feat/<name>` and `fix/<name>` for small changes. Commit focused changes.

## CI pipeline
On push/PR: install pinned runtimes; install from lockfiles; formatting check; lint; TypeScript check; frontend tests; Ruff; pytest; build frontend; API contract tests; dependency/security checks where available. E2E can be separate if it requires services.

## Deployment flow
1. Implement one task.
2. Run local checks.
3. Commit.
4. CI checks.
5. Deploy preview.
6. Smoke test login, lecture manifest, MCQs, progress, media.
7. Apply migration to development first.
8. Verify and merge.
9. Deploy main.
10. Inspect logs/health.
11. Update PROGRESS.md.

## Database changes
Versioned migrations only; test from empty and previous schema. Prefer additive changes. Backup before destructive operations. Stop deployment if migration fails. Prefer forward fixes; never assume schema rollback is safe after writes.

## Rollback
Application: redeploy last known-good deployment/commit.
Database: forward-fix where possible; restore only with explicit decision and understood data loss.
Media: retain prior asset until replacement validated.

## Secrets and prototype limits
Secrets belong in provider secret stores/local ignored `.env`; never in frontend or CI logs. Render Free may sleep; local grader is not always available; free-plan terms can change. Do not claim 100-user capacity without measured tests.
