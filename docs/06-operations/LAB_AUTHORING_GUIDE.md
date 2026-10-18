# Lab authoring guide (practical labs, pack schema v2)

Each lecture's lab is ONE JSON file in `content/lectures/NNN-short-title.json` (see `backend/app/content_pack.py` for the exact schema and
`docs/01-product/PRACTICAL_LABS_SPEC.md` for the product rules). The practical project each lab must implement is the
`practical_project` text of that lecture in `content/course.json` (taken from the course document). Keep to it: a lab may simplify the
project to fit one code file, but it must build the same thing and demonstrate the same idea.

## The learner's experience (what the pack must support)
- The learner reads the task (objective, instructions, constraints, "you will pass when"), sees any **files provided**, writes Python in
  one editor, presses **Run** (output only) and **Save & check**. The check runs instantly in the browser on the *visible* checks, then
  officially on the server on *all* checks. Pass = every check passes. No partial scores.
- On failure a popup lists the failed checks (by their labels) and any exception with its line; **Show hint** shows each failed check's
  `remediation` text. So every check needs a remediation that says what to change, not just what is wrong.
- The bulb gives the 3 general `hints` in order (hint 1 = nudge, hint 2 = the approach, hint 3 = almost the code). After 3 the learner
  can Redo.
- Students are Class 8+ beginners. Plain words, short sentences, one idea per check. Never require `input()` (there is no stdin).

## Pack rules (enforced by `scripts/content_pack.py validate` and `scripts/verify_labs.py`)
- `schema_version: 2`, `lecture_number`, `title`, `summary`, `objectives`, `duration_minutes`, `prerequisites: [previous lecture number]`.
- `lab_only: true` until the lecture's teaching content exists: segments are just `intro` (body: what the learner will build, 3-6 sentences,
  Markdown) and `exercise`. Lectures that already have readings and checkpoints keep them (`lab_only: false`) and only the `lab` changes.
- `lab.kind: code`, `lab.scoring: pass_fail`, `lab.hints` = exactly 3, `lab.hints_max: 3`, `lab.hint_penalty_percent: 0`.
- `lab.starter_code`: a scaffold with numbered comments; it must NOT pass the checks on its own. `lab.solution`: a reference solution that
  passes every check; it is verified and never shown or imported.
- `lab.visible_examples`: 1-2 runnable examples with `expected_output` (a smaller/variant version of the task, never the solution).
- `lab.success_criteria`: the learner-facing list; one line per check.
- `lab.tests`: 3-6 checks. Each has `key` (`lNN-tK`), `label` (learner-facing), `remediation` (how to fix), `objective` (the skill),
  `hidden` (true for at least one; hidden checks are the ones a learner could otherwise hard-code around) and either an inline
  `definition` (visible checks) or an entry under the same key in the private hidden-definitions file (hidden checks).
- `lab.packages`: only what the lab imports, from numpy, pandas, matplotlib, scikit-learn, pillow, requests.
- `lab.assets`: small data files the program reads (`name`, `content`; ≤ 20 KB each). Fictional data only.
- Deterministic: no randomness, no dates, no network except the practice API.

## Check definitions (host-evaluated; see `grader/grader_service/evaluate.py`)
| definition | passes when |
|---|---|
| `{"match": "non_empty"}` | the program printed something |
| `{"expected_stdout": "..."}` | the whole output equals this (trimmed) |
| `{"expected_stdout_lines": ["a", "b"]}` | the non-empty output lines equal these |
| `{"stdout_contains": "text", "ignore_case": true}` | output contains the text |
| `{"stdout_regex": "^Total: \\d+$"}` | a line matches (multiline) |
| `{"stdout_min_lines": 3}` | at least N non-empty lines |
| `{"check": "variable_is_str", "name": "x"}` / `{"check": "variable_type", "name": "x", "type": "int"}` | a top-level variable exists with that type (`int`, `float`, `bool`, `str`, `list`, `dict`, `tuple`, `set`) |
| `{"check": "variable_equals", "name": "x", "value": 60}` | a top-level scalar variable equals the value |
| `{"check": "stdout_equals_variable", "name": "x"}` | the output equals the string variable |
| `{"expr": "<python expression>", "expected": <json>}` | the expression, evaluated in the learner's namespace after the program ran, equals the value (numbers ±1e-6, strings trimmed, lists/dicts compared deeply) |
| `{"expr": "...", "expected_in": [..]}` / `{"expr": "...", "truthy": true}` | the value is one of / is truthy |
Probe expressions may call the learner's functions and classes (`callable(area)`, `area(2) == 12.57`, `Pet('Rex').introduce()`), inspect
files the program wrote (`open('notes.txt').read()`), or use `__import__('json').load(open('catalogue.json'))`. They must be total:
wrap anything that can fail in a way that yields False rather than an exception, or accept that an exception = not passed.

## The practice API (lecture 23 onward)
`https://api.neuromind.lab/v1` with test key `nm-test-key-123`; endpoints in `docs/01-product/PRACTICAL_LABS_SPEC.md` §6 and
`grader/sandbox/labmock.py`. Add `"requests"` to `packages`; nothing else on the internet is reachable.

## Workflow
1. Write the pack and the hidden definitions (`private/exercise_tests_<block>.json`, git-ignored).
2. `backend/.venv/bin/python scripts/content_pack.py validate content/lectures`
3. `backend/.venv/bin/python scripts/verify_labs.py content/lectures --numbers N` — solution must pass, starter must fail.
4. Import as published: `scripts/content_pack.py import content/lectures/NNN-*.json --tests private/... --yes --publish [--replace]`.
