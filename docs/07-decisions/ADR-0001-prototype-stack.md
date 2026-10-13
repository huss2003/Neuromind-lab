# ADR-0001: Free-tier/local-first prototype
Status: Accepted for prototype | Date: 2026-10-13

## Context
Solo developer must show working flow before budget approval.

## Decision
React/TypeScript; Cloudflare Pages Free; FastAPI local or Render Free preview; Supabase Free; GitHub; Pyodide practice; local Docker official grading; Google Drive for source assets and R2/HTML5-compatible media tested for transitions. No Redis, paid AI API, paid hosting or GPU until approval.

## Alternatives
Railway Pro immediately: deferred due to recurring cost before proof.
Cloudflare Workers as entire API: not primary because Python API/local grader workflow is simpler with FastAPI.
Hosted grader: deferred until security/budget review.

## Consequences
Low cost, easy local debugging and replaceable components; but cold starts, quotas and local grader availability limit production suitability. No production security/capacity guarantee.

## Revisit
When budget approved, real learners need reliability, or hosted code execution is required.
