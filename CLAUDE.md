# CLAUDE.md — NeuroMind AI Learning Lab
Read README, PROGRESS.md and relevant specs before coding.

## Mission
Build one data-driven sample lecture first. Developer is solo. Make small, reviewable changes.

## Source-of-truth hierarchy
PRD -> acceptance criteria -> data model/API -> architecture -> security/test plan -> code/tests. If docs conflict, stop and report the conflict; do not silently choose.

## Always
- Inspect repository before editing.
- Select one task from implementation plan.
- List intended files and acceptance criteria first.
- Add/update tests with each behaviour change.
- Run lint, typecheck, tests and relevant E2E tests.
- Use SQL migrations; keep OpenAPI and schema docs aligned.
- Use TypeScript strict mode and Python type hints/Pydantic models.
- Keep lecture timeline logic in a dedicated module.
- Enforce auth/ownership on every protected backend operation.
- Keep official score/completion server-authoritative.
- Make retries idempotent.
- Use accessible labels, visible focus and loading/error/success states.
- Update PROGRESS.md after each session.
- Report actual tests run and failures honestly.

## Never
- Never build 104 bespoke lecture pages.
- Never expand scope without approval.
- Never execute arbitrary student code inside API process.
- Never expose Docker socket/daemon, host files, secrets or hidden tests.
- Never allow network access from student code by default.
- Never trust client-provided role, user ID, score, correctness or completion.
- Never put service-role keys or secrets in frontend/VITE variables.
- Never commit `.env`, tokens, credentials or real learner data.
- Never add paid hosting, Redis, paid AI APIs or GPU infrastructure without approval.
- Never claim 100-user capacity or production-grade security without tests.
- Never weaken/skip tests just to get a green build.
- Never render student output as HTML.
- Never rely on undocumented Drive iframe behaviour for required transitions.

## Conventions
Frontend: functional React components, named exports by default, PascalCase components, camelCase functions, API calls in service layer, semantic HTML. Avoid broad `any`.
Backend: thin routers, business rules in services, explicit Pydantic request/response models, UTC timestamps, safe structured errors, no secrets in logs.
Database: snake_case, numbered migrations, constraints/indexes/RLS documented.
Provider integrations: use small adapters when replacement is plausible.

## Task workflow
1. Read spec/current code.
2. State planned change and tests.
3. Check schema/security/cost impact.
4. Implement only task.
5. Run checks.
6. Report changed files and test results.
7. Update PROGRESS.md.

## Definition of done
Acceptance criteria pass; tests pass or limitation is explicit; no secret leak; docs updated; PROGRESS updated; no non-goal violation. Ask before changing API/schema/security/cost/scope/retention decisions.
