# Production release checklist

Mandatory gates must all be ticked with evidence. Current state is in the readiness report: **CONDITIONAL GO (supervised pilot)**; unticked items below are the conditions.

## Mandatory gates
- [~] **G0 Secrets (partly):** all synthetic accounts deleted 2026-10-14 and the old password verified dead; the service-role key was NOT rotated (owner decision). Original item:  the Supabase service-role key is rotated and the new value is in Vercel only; dev accounts' passwords are changed or the accounts deleted; Git history reviewed (the old default password is in public history).
- [ ] **G0 Hidden tests:** the real assessment definitions exist only in the private store; none in Git, bundles, or responses.
- [x] CI exists (`.github/workflows/ci.yml`) and a local secret scan passes. [x] CI ran on GitHub (PR 1): secrets, grader and frontend passed; backend failed on a test that needed local env vars, fixed to be hermetic.
- [x] **G1** Full learner journey passes against real services (`E2E_LEARNER_JOURNEY.md`).
- [x] **G2** Docker sandbox adversarial run passes (CPU, memory, pids, network, filesystem, metadata, escape probes).
- [x] **G3** Hosted worker runs privately; restart, duplicate, lease-expiry and dead-letter behaviours demonstrated in staging.
- [x] **G4** Real content for the launch lecture (9) and Lectures 10 to 12; teacher scope tests; axe scans. [ ] manual screen-reader pass. [ ] load objectives fully met (dashboard p95 and submit ack p95 missed by a small margin; see LOAD_TEST_PLAN).
- [ ] Migrations 0001–0006 and seeds applied to staging first; backup taken before production changes.
- [x] Smoke test on production with a synthetic account, including a real hosted grade.
- [x] Restore rehearsed locally from a JSON backup (`BACKUP_RESTORE_RUNBOOK.md`); rollback = re-alias previous Vercel deployment (documented, not exercised).
- [x] Billing alert configured; AWS resource inventory current (adds SNS topic, 4 CloudWatch alarms, queue-monitor timer). [ ] SNS e-mail subscription confirmed by the owner.

## Not required for first release (future)
Authoring UI, named cohorts, admin dashboards, queue metrics screens, report-an-issue form, AI tutor, 103 more lectures.
