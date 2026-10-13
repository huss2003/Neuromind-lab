# Prompt Library

## Start session
Read README, CLAUDE.md, AGENTS.md, PROGRESS.md and relevant specs. Inspect repository and report current state without editing. Identify next incomplete task, dependencies, acceptance criteria, risks and files. Ask if prerequisite is missing.

## Implement one task
Implement only task [ID/title] from IMPLEMENTATION_PLAN. First list files and map criteria to tests. No unrelated features/dependencies. Add tests, run lint/typecheck/tests, report actual results, update PROGRESS. Stop for ambiguous scope/security/cost decisions.

## Generate tests
Read story/specs. Create happy path, invalid input, permission, retry/idempotency, persistence and failure tests before changing implementation.

## Review diff
Check correctness, access control, hidden data exposure, races, missing tests, accessibility, scope creep and version drift. Rank findings by severity and cite file/line. Do not rewrite everything immediately.

## Security-review grader
Verify code is not run in API process; no Docker socket/secrets/host mounts; network disabled; CPU/memory/process/time/output limits; cleanup; hidden tests protected; output treated as text; infra failure not student failure. Do not call Docker alone production-secure.

## Add lecture content
Use existing manifest schema; no new player page. Include ordered segments, MCQs, practical video, exercise, tests and completion rules. Use placeholders where recording is not ready. Add content validation.

## Debug failure
Reproduce; inspect spec and root cause; make smallest fix. Never weaken assertions or skip tests. Run regression suite and update progress.

## Change schema
Propose versioned migration, data impact, RLS/index/API/type/test changes and rollback/forward-fix. Wait for approval for destructive changes.

## Cost/provider review
Separate verified current pricing from assumptions; inspect quotas, cold starts, ephemeral storage, billing and privacy. Do not add paid service or change ADR without approval.

## Prepare demo
Verify sign-in, two MCQs, transitions, practical, browser run, official local grade, fail/retry, resume and teacher results. Clearly mark placeholders and limitations; no unsupported scale/security claims.

## End session
Update PROGRESS with date, task, summary, files, commands/tests and actual results, decisions, open issues and next task. Never mark unverified work complete.
