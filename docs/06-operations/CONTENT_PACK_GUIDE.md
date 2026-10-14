# Content pack guide (how the 104 lectures get uploaded)

One JSON file per lecture in `content/lectures/` (name it `NNN-short-title.json`). One tool imports them all: `scripts/content_pack.py`. No per-lecture scripts and no code changes per lecture.

## What a pack contains
`schema_version` (1), `lecture_number` (1 to 104), `title`, `summary`, `objectives`, `duration_minutes`, `prerequisites` (earlier lecture numbers), then:
- `checkpoints`: multiple-choice questions (`key`, `type` mcq or exit_check, `question` with options, `correct_option_id` and both explanations). The exit check defaults to a 100 percent pass threshold.
- `segments`: the ordered lesson. Types: intro, reading, example, checkpoint, exercise, exit_check. Text segments need a `body` (Markdown). Checkpoint segments name a checkpoint `key`. An example may set `opens_exercise`. The last segment must be the exit check, and there must be exactly one exercise.
- `lab`: title, objective, instructions, starter code, hints, visible examples, success criteria and `tests`. Each test has a `key`, a learner-facing remediation, an objective, the earlier segment to send the learner back to (`remediation_segment`), and `hidden`. At least one test must be hidden.

## Hidden answers stay out of Git
The pack holds only test **keys**. The real definitions (expected output etc.) go in a git-ignored file under `private/`, a JSON object `{ "test-key": { ...definition... } }`, passed with `--tests`.

## Commands
```
backend/.venv/bin/python scripts/content_pack.py validate content/lectures        # offline; CI runs this on every push
backend/.venv/bin/python scripts/content_pack.py import content/lectures/013-x.json --tests private/t13.json          # dry run, writes nothing
backend/.venv/bin/python scripts/content_pack.py import content/lectures/013-x.json --tests private/t13.json --yes     # writes as DRAFT (learners cannot see it)
backend/.venv/bin/python scripts/content_pack.py import content/lectures/013-x.json --tests private/t13.json --yes --publish   # makes it live
```
Re-importing the same pack updates the same rows (ids come from the lecture number), so fixing a typo is: edit the JSON, validate, import. Importing a draft over a published lecture is refused unless `--force`, so a mistake cannot silently unpublish live content. Take a backup first (`scripts/backup_db.py`) before importing to production.

## Importing from the browser
Administration > Content > **Import a lecture**: choose the pack and the hidden-tests file, press **Check pack** (lists every problem in plain words), then **Import as draft** (or tick publish). A published lecture is protected from being turned back into a draft unless you tick the replace box. The same rules and validator as the command line apply, and the hidden tests are stored server-side only. After importing a draft, review it, then change its status to Published in the table below (this also publishes its questions and lab).

## Checks the validator makes
Unique option ids and texts; the correct option exists; checkpoints and segments agree in order and type; one exercise and one exit check; remediation points before the lab; prerequisites are earlier lectures; no unknown fields; no duplicate lecture numbers across packs.

## Status
Lectures 10 to 12 are converted to packs and rebuild byte-identical rows to the original script (checked once, 2026-10-14). Lecture 9 uses video segments and is still loaded by its original seed; converting it needs a `video` segment type (not built).
