# Error Handling and Edge Cases

Principle: explain the problem, preserve valid state, offer a safe recovery, and never mislabel infrastructure failure as learner failure.

## Auth/permissions
- Expired session -> re-authenticate and preserve safe return route.
- Invalid token -> 401, no protected data.
- Learner on teacher route -> 403.
- Cross-user ID -> 404/403 without leaking data.
- Missing role -> deny privileged actions.
- Auth provider unavailable -> service error, no fake session.

## Media/lecture
- Missing/403/404 media -> retry/content report; do not silently advance.
- Drive iframe has no reliable end event -> do not rely on it; use fallback or HTML5 source.
- Autoplay blocked -> show continue button.
- Duplicate ended event -> transition once.
- Refresh at checkpoint -> restore checkpoint.
- Seeking past required checkpoint -> block/restore; server enforces.
- Progress save failure -> visible unsaved/retry state.
- Changed content version -> safe recovery.
- Practical ends but exercise missing -> content error, not completion.
- Segment cycle/duplicate order -> publishing validation rejects.

## MCQ
- No option -> validation.
- Unknown option/wrong checkpoint -> 422.
- Answer key in learner response -> release-blocking test failure.
- Duplicate network retry -> same idempotent result.
- Same idempotency key with different payload -> 409.
- Missing explanation -> safe fallback; publishing should validate.
- Attempt limit -> clear message.
- Client result differs from server -> server result wins.

## Browser coding
- Monaco/Pyodide fails -> retry/fallback; do not crash player.
- Unsupported package -> explain limitation.
- Infinite loop -> terminate worker with timeout.
- Huge output -> truncate and explain.
- Tab closes mid-run -> no assumed official result.
- Output includes HTML/script -> render as text.
- Browser/server outputs differ -> practice label; official server result authoritative.

## Grader
- Worker unavailable/crashes -> retryable infrastructure error, not student fail.
- Timeout/memory/process limit -> terminate and safe status.
- Container cannot start -> infrastructure error.
- Hidden test fails -> safe category/hint, no expected values.
- Cleanup fails -> log/alert and cleanup; do not reuse dirty container.
- Network attempt -> denied.
- Duplicate submission -> idempotent.
- Result persistence fails -> do not show final official success.

## Database/API
- DB timeout -> controlled 503/retry, no false completion.
- Constraint violation -> safe 409/422.
- Invalid UUID -> 422.
- Stale version -> conflict response.
- Migration fails -> stop deployment.
- Free project paused -> service unavailable/local fallback.
- Rate limit -> 429 with retry guidance.
- Unexpected response -> client catches and shows recoverable error.

## Teacher/UI
- Invalid content references or no grading tests -> block/warn on publish.
- Published question edit -> new version.
- Concurrent edits -> version conflict.
- No results -> empty state.
- Every async action has loading/error/success state; never green success before server confirmation.
