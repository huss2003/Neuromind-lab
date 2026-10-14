# Phase 7 plan: content pipeline (so the 104 lectures can be added without code changes)

**Why:** every checklist and tracker phase that can be finished from code is done; the remaining product gap is content, and the PRD says authors must not edit code for routine content. Lectures 10 to 12 were loaded by one bespoke script, which does not scale to 104.

**Scope (this change only):** pack format + validator + deterministic row builder (`backend/app/content_pack.py`), a CLI (`scripts/content_pack.py`: validate / import with dry run, draft-by-default, publish flag, unpublish guard), packs for lectures 10 to 12, CI validation, guide.
**Not in scope:** an in-browser authoring UI, video segments, importing hidden tests from Git, any schema change (no migration needed), any API change.
**Impact:** schema none; security: hidden definitions stay in `private/`, import uses the service key from `.env` locally only; cost none.
**Acceptance:** packs validate; rows equal the legacy script's rows; defects are reported by field; re-import is idempotent; draft import cannot unpublish; CI runs the validator; guide explains the workflow.
**Tests:** `backend/tests/test_content_pack.py` (20), plus the one-off equivalence check recorded in the guide.
**Next candidates (need your decision):** a `video` segment type to convert Lecture 9; admin upload screen for packs; bulk "publish range" command.
