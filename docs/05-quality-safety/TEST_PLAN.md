# Test Plan

## Tools
Frontend: Vitest + Testing Library. E2E: Playwright. Backend/worker: pytest. Static checks: TypeScript, ESLint, Prettier, Ruff. Later load tests: k6 or Locust.

## Coverage targets
Aim for 80% coverage of critical backend business logic (scoring, transitions, permissions) and 70% of core frontend logic where practical. All security-critical acceptance cases must be tested. Coverage does not replace meaningful assertions.

## Unit tests
- Segment order, `ended` transition, duplicate event, checkpoint pause/bypass, missing segment.
- Correct/incorrect MCQ, invalid option, wrong checkpoint, answer-key absence, idempotency.
- Progress ownership, stale version, resume, completion prerequisites.
- Grader pass/fail, timeout, worker unavailable, output truncation, resource limits, cleanup, no network/secrets.
- Teacher authorisation, publish validation, content versioning.

## Integration tests
- Supabase token verification.
- Published lecture manifest.
- MCQ attempt persistence.
- Progress persistence.
- Submission state lifecycle.
- RLS with two learners and teacher.
- Migrations from empty DB; idempotent seed data.
- Teacher route scope.

## E2E-01 happy path
Sign in -> Lecture 9 -> segment -> MCQ1/result -> segment -> MCQ2/result -> practical video -> auto-open exercise -> Pyodide run -> official local grading -> pass -> exit check -> completion.

## E2E-02 fail/retry
Submit incorrect code; receive failed result and safe feedback; retry with correct code; pass; both attempts remain.

## E2E-03 resume
Complete first checkpoint, refresh/reopen, verify correct state and no bypass.

## E2E-04 permissions
Learner tries teacher route and another learner's submission; both denied.

## E2E-05 dependency failure
Simulate media/API/grader failure; verify recoverable error and no false completion/failure.

## Accessibility/browser
Keyboard-only core flow, visible focus, labels, 200% zoom, reduced motion, contrast and non-colour status. Primary browser Chrome/Edge current stable; smoke-test Firefox/Safari where available; viewport 360/768/1280/1440.

## Exit criteria
Core E2E happy/fail/retry/resume pass; no known critical/high issue for demo threat model; no secrets in Git; migrations and fresh setup work; limitations documented.
