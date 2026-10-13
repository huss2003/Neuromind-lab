# ADR-0003: Browser practice plus official grading
Status: Accepted | Date: 2026-10-13

## Context
Browser execution is responsive and cheap but not authoritative; server execution is needed for consistent grading.

## Decision
Pyodide for supported practice; local Docker worker for official grading during development. Backend owns score/completion. Worker is separate from API, local-only, constrained, no network/secrets by default. Provide adapter for future hosted worker.

## Consequences
Low prototype cost; browser/server environments can differ; local grading is not always available remotely; Docker alone is not complete hostile-code isolation.
