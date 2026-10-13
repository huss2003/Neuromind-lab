# Security Requirements

## Threat model
Assets: identities, progress, attempts/scores, hidden answers/tests, source submissions, provider secrets, grading host. Threats: score tampering, IDOR, role escalation, malicious Python, dependency compromise, secret exposure.

## Authentication/authorisation
- Supabase Auth; API validates tokens and derives user ID from verified claims.
- Role is trusted server-managed data, never client-controlled.
- Verify ownership on every read/write, including submission-result lookup.
- Learner accesses only own records; teacher access is course-scoped.
- UI hiding is not security.

## Secrets
- Commit `.env.example`, never `.env`.
- Service-role key and provider credentials are server-only.
- Never use `VITE_` for secrets.
- Never pass secrets into grading containers or log tokens.
- Rotate leaked credentials; use separate dev/prod credentials.

## Input and application security
Validate IDs, payload shape, code size, option IDs, segment/question/exercise references, attempt limits, URLs/hosts, output size and pagination. Use parameterized DB access. Escape output and never render learner output as HTML. Restrict CORS to expected origins. Avoid arbitrary backend URL fetching (SSRF). Apply request/usage limits.

## Student code execution — critical
Prototype grader is local-only unless separately reviewed. Run outside API process; use non-root container; time/CPU/memory/process/file/output limits; read-only root where feasible; disposable temp dir; no network by default; no host home/repository/credential mounts; no Docker socket; no inherited secrets; cleanup after each job; hidden tests server-side; output treated as untrusted text. Restrict supported packages where practical. Docker alone is not complete isolation; public production execution may require stronger sandboxing and security review.

## OWASP-relevant risks
Broken access control/IDOR; injection; security misconfiguration; authentication/session failure; SSRF; unrestricted resource consumption; sensitive data exposure; insecure design/state bypass; vulnerable dependencies; insufficient logging; XSS; CORS mistakes.

## RLS and database
Enable RLS on browser-accessible tables. Learners cannot directly set role, score, correctness, hidden test results or completion. Test with two learners and teacher. Keep service-role key out of browser.

## Media
Use non-sensitive demo videos. Test CORS/range playback. Do not depend on unguessable URLs as access control. Do not fetch arbitrary user-supplied media URLs from backend.

## Logs/retention
Never log passwords, tokens, secrets or hidden tests. Define source-code retention before real learners. Log safe request IDs, permission failures and infrastructure errors.

## Release gate
Do not expose public arbitrary-code execution until worker isolation, limits, auth/RLS, hidden-test protection, timeout tests, secret checks and security review pass. For boss demo, use synthetic data and controlled local grading.
