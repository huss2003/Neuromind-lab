# Non-Functional Requirements

## Prototype performance targets (not guarantees)
- Warm main UI interactive <3 seconds on typical broadband desktop.
- Warm API reads p95 <800 ms.
- Warm MCQ submission/progress save p95 <1.5 seconds.
- Small supported browser practice feels immediate; timeout guard required.
- Trivial local grading target <5 seconds excluding startup.
- Resume restores latest saved state when network is available.
Free-tier cold starts may violate targets; record actual measurements.

## Reliability
No uptime SLA for prototype. Recover from media/API/grader failures. Never show official success without trusted result. Idempotent retries and server-persisted state.

## Capacity
Future goal: 100 concurrent learner sessions. Prototype must not claim 100 concurrent code executions. Test 100 sessions separately from simultaneous grading at 10/25/50/100 jobs. Record p50/p95, errors, CPU/RAM, queue wait and cost.

## Accessibility
Target WCAG 2.2 AA for key flow: keyboard, visible focus, labels, errors, contrast, semantic structure, reduced motion, accessible checkpoint focus, captions/transcripts where feasible.

## Browser/device
Desktop-first coding; current Chrome/Edge primary, Firefox/Safari smoke tests, responsive tablet/mobile. Do not claim untested browser support.

## Maintainability/observability
Typed contracts, migrations, provider adapters, lockfiles, request IDs, safe logs, grading duration/status and failed progress saves. Never log secrets or hidden tests.

## Privacy/durability
Supabase stores durable prototype progress; never rely on Render local disk. Keep video outside DB. Define source-code retention before real learners. Use synthetic data for demo.

## Cost
Target ₹0 recurring prototype using free/local resources. No paid service without approval. Check quotas/billing controls. Re-estimate production after load/video tests.
