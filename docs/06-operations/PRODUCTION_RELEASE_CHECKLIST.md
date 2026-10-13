# Production release checklist

Mandatory gates must all be ticked with evidence. Current state is in the readiness report: **NO-GO**.

## Mandatory gates
- [ ] **G0 Secrets:** the Supabase service-role key is rotated and the new value is in Vercel only; dev accounts' passwords are changed or the accounts deleted; Git history reviewed (the old default password is in public history).
- [ ] **G0 Hidden tests:** the real assessment definitions exist only in the private store; none in Git, bundles, or responses.
- [x] CI exists (`.github/workflows/ci.yml`) and a local secret scan passes. [ ] CI has actually run on GitHub.
- [ ] **G1** Full learner journey passes against real services (`E2E_LEARNER_JOURNEY.md`).
- [ ] **G2** Docker sandbox adversarial run passes (CPU, memory, pids, network, filesystem, metadata, escape probes).
- [ ] **G3** Hosted worker runs privately; restart, duplicate, lease-expiry and dead-letter behaviours demonstrated in staging.
- [ ] **G4** Real (non-placeholder) content for the launch lecture; teacher scope tests; accessibility pass (axe + manual keyboard/screen reader); load test at the agreed capacity with thresholds fixed beforehand.
- [ ] Migrations 0001–0006 and seeds applied to staging first; backup taken before production changes.
- [ ] Smoke test on production with a synthetic account, including a real hosted grade.
- [ ] Rollback and restore procedures rehearsed.
- [ ] Billing alert configured; AWS resource inventory current.

## Not required for first release (future)
Authoring UI, named cohorts, admin dashboards, queue metrics screens, report-an-issue form, AI tutor, 103 more lectures.
