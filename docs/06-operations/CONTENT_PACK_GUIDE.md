# Content pack guide (how the 104 lectures get uploaded)

One JSON file per lecture in `content/lectures/` (name it `NNN-short-title.json`). One tool imports them all: `scripts/content_pack.py`. No per-lecture scripts and no code changes per lecture.

## What a pack contains
`schema_version` (2; 1 is still accepted), `lecture_number` (1 to 104), `title`, `summary`, `objectives`, `duration_minutes`, `prerequisites` (earlier lecture numbers), then:
- `checkpoints`: multiple-choice questions (`key`, `type` mcq or exit_check, `question` with options, `correct_option_id` and both explanations). The exit check defaults to a 100 percent pass threshold.
- `segments`: the ordered lesson. Types: intro, reading, example, checkpoint, exercise, exit_check. Text segments need a `body` (Markdown). Checkpoint segments name a checkpoint `key`. An example may set `opens_exercise`. The last segment must be the exit check, and there must be exactly one exercise.
- `lab`: title, objective, instructions, starter code, hints, visible examples, success criteria and `tests`. Each test has a `key`, a learner-facing remediation, an objective, the earlier segment to send the learner back to (`remediation_segment`), and `hidden`. At least one test must be hidden.

## Schema v2 (practical labs, 2026-10-16)
- `lab_only: true` — the lecture has no teaching content yet: one `intro` segment plus the `exercise` segment, no checkpoints and no exit check. Every lecture from 13 onwards is imported this way until its lesson is uploaded; the pack is then extended (not replaced) with readings and checkpoints.
- `lab.kind`: `code` (auto-checked), `quiz` (question set in `lab.questions`, marked on the server), `written` (text answer, teacher marks it from `lab.rubric`), `upload` (link plus `lab.checklist`, teacher marks it from the rubric).
- `lab.scoring`: `pass_fail` (default for new labs: every check must pass, hints capped at `hints_max` = 3 per cycle, then **Redo**) or `score` (the old percentage mode with `pass_threshold`).
- `lab.packages` (numpy, pandas, matplotlib, scikit-learn, pillow, requests), `lab.assets` (small fictional data files: `name`, `content`, `encoding` text or base64, `description`), `lab.limits` (`memory_mb`, `timeout_seconds`).
- `lab.solution`: the reference solution. It is verified by `scripts/verify_labs.py` (solution passes every check, starter code fails at least one) and is never imported or shown.
- Visible checks (`hidden: false`) carry their `definition` inline so the browser can run the quick check. **Hidden checks must not**: their definitions stay in the git-ignored `private/` file and the validator rejects a hidden check with an inline definition. Inline definitions take precedence over entries with the same key in the private file.
- Check kinds and the predefined practice API are described in LAB_AUTHORING_GUIDE.md and PRACTICAL_LABS_SPEC.md.

## Hidden answers stay out of Git
The pack holds only test **keys**. The real definitions (expected output etc.) go in a git-ignored file under `private/`, a JSON object `{ "test-key": { ...definition... } }`, passed with `--tests`.

## Commands
```
backend/.venv/bin/python scripts/content_pack.py validate content/lectures        # offline; CI runs this on every push
backend/.venv/bin/python scripts/verify_labs.py content/lectures --numbers 9-24 --tests private/exercise_tests_block1_a.json   # runs solutions and starters through the real grader checks
backend/.venv/bin/python scripts/content_pack.py course --yes                      # course, 13 month-modules and lecture records from content/course.json
backend/.venv/bin/python scripts/content_pack.py export 10 --out content/lectures/010-x.json   # database -> pack (hidden checks to private/)
backend/.venv/bin/python scripts/content_pack.py import content/lectures/013-x.json --tests private/t13.json          # dry run, writes nothing
backend/.venv/bin/python scripts/content_pack.py import content/lectures/013-x.json --tests private/t13.json --yes     # writes as DRAFT (learners cannot see it)
backend/.venv/bin/python scripts/content_pack.py import content/lectures/013-x.json --tests private/t13.json --yes --publish   # makes it live
```
Re-importing the same pack updates the same rows (ids come from the lecture number), so fixing a typo is: edit the JSON, validate, import. Importing a draft over a published lecture is refused unless `--force`, so a mistake cannot silently unpublish live content. `--replace` swaps a lecture's sections, checks and lab for the pack's (the lecture id is kept, so prerequisite links and progress rows stay valid); it is refused without `--force` once learners have attempted the lab. The `--tests` option is repeatable, so one block's private files can be passed together. Take a backup first (`scripts/backup_db.py`) before importing to production.

## Importing from the browser
Administration > Content > **Import a lecture**: choose the pack and the hidden-tests file, press **Check pack** (lists every problem in plain words), then **Import as draft** (or tick publish). A published lecture is protected from being turned back into a draft unless you tick the replace box. The same rules and validator as the command line apply, and the hidden tests are stored server-side only. After importing a draft, review it, then change its status to Published in the table below (this also publishes its questions and lab).

## Checks the validator makes
Unique option ids and texts; the correct option exists; checkpoints and segments agree in order and type; one exercise and one exit check; remediation points before the lab; prerequisites are earlier lectures; no unknown fields; no duplicate lecture numbers across packs.

## Status
2026-10-16: lectures 9 to 12 are full packs (readings, checkpoints and the new practical labs from the course document); lectures 13 to 24 are `lab_only` packs (Block 1). All 16 pass `verify_labs.py`. Hidden definitions for Block 1 live in `private/exercise_tests_block1_{a,b,c,d}.json` (git-ignored; back them up with the database). The old private files for the previous lecture 9 to 12 labs are kept under `private/old/`.
