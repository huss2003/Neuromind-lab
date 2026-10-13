"""Generates database/seed/005_lecture9_content.sql (real Lecture 9 content, no hidden test definitions)."""
import json

L = "00000000-0000-4000-8000-000000000009"
def q(s): return "'" + s.replace("'", "''") + "'"
def j(o): return q(json.dumps(o, ensure_ascii=False)) + "::jsonb"

INTRO = """## What you will do today

By the end of this lecture you will have Python running, you will know how a notebook works, and you will have written and submitted your first program.

- Set up Python and check that it works
- Run code and text in a notebook
- Store information in a variable and show it with `print()`

The lecture has three short readings, two knowledge checks, one coding lab and a short exit check. Leave whenever you need to; you resume where you stopped.

Knowledge checks show you how you are doing. The lab and the exit check decide whether the lecture is complete. In the lab you can try as often as you like and your best score is the one that counts."""

SETUP = """## Two ways to start

You need Python 3 to run the code in this course. Pick one route.

**On your own computer.** Download Python 3.12 or newer from python.org and run the installer. On Windows, tick *Add python.exe to PATH* before you click Install.

**In your browser.** If you cannot install software, use a hosted notebook service such as Google Colab. Python is already installed there.

## Check that it works

Open a terminal (Command Prompt or PowerShell on Windows, Terminal on macOS and Linux) and run:

```
python --version
```

You should see something like `Python 3.12.4`. On macOS and Linux the command is often `python3 --version`.

If the terminal says the command was not found, Python is installed but your computer cannot find it yet. Close the terminal, open a new one and try again. If it still fails on Windows, run the installer again, choose *Modify*, and tick the PATH option."""

NOTEBOOKS = """## What a notebook is

A notebook is a document that mixes code, the output of that code, and text. People use notebooks because you can run a small piece, look at the result, and change your mind.

## Cells

A notebook is made of cells. You will use two kinds:

- **Code cells** hold Python. When you run one, its output appears directly beneath it.
- **Text cells** (Markdown) hold notes and headings. They do not run as code.

To run the selected cell, press `Shift + Enter`. The notebook runs it and moves to the next cell.

## The kernel remembers

Behind the notebook is a running Python process called the kernel. Every cell shares it. If one cell contains:

```
x = 5
```

then a later cell containing `print(x)` shows `5`, for as long as the kernel is running.

Order matters. Cells run in the order you run them, which is not always top to bottom. When a result looks wrong, restart the kernel and run every cell from the top."""

FIRST = """## Your first program

A program is a list of instructions that Python follows one line at a time. Here is a complete one:

```
student_name = "Aarav"
print(student_name)
```

Running it shows:

```
Aarav
```

## What each line does

- `student_name = "Aarav"` creates a **variable**. The name goes on the left, the value on the right, and `=` stores the value under that name. Text must be wrapped in quotes.
- `print(student_name)` shows the value on screen. There are no quotes around `student_name`, because you are printing what the variable holds, not the word itself.

## Changing a variable

A variable can be given a new value at any time. Python works out the right-hand side first:

```
price = 20
price = price + 5
print(price)
```

This prints `25`. Python reads `price + 5` using the old value (20), then stores the answer back under `price`.

## Common mistakes

- `print("student_name")` with quotes prints the words, not the value.
- One `=` stores a value. Two, `==`, compare two values; you will use that later.
- A missing closing quote or bracket causes a `SyntaxError`. Python tells you which line.

You will practise all of this in the lab next."""

stmts = []
stmts.append(f"""update public.courses set title = 'NeuroMind AI Foundations',
  description = 'A practical path from your first Python program to building and understanding AI systems. You learn by writing code that is graded fairly, with help the moment you need it.'
  where id = '00000000-0000-4000-8000-000000000001';""")
stmts.append("""update public.modules set title = 'Python for AI',
  description = 'Set up your tools and write the code that every later lecture builds on.'
  where id = '00000000-0000-4000-8000-000000000002';""")
stmts.append(f"""update public.lectures set
  summary = 'Set up Python, run your first notebook cell, and write a program that stores and prints information.',
  learning_objectives = {j(["Check that Python is installed and working", "Run code cells and text cells in a notebook", "Store a value in a variable with =", "Show a result with print()"])},
  duration_seconds = 2100, content_version = 2
  where id = '{L}';""")
seg = lambda sid, typ, title, settings: (
    f"update public.lecture_segments set segment_type = '{typ}', title = {q(title)}, media_provider = null, media_url = null, "
    f"media_asset_key = null, duration_seconds = null, settings = {j(settings)} where id = '{sid}';")
stmts.append(seg("00000000-0000-4000-8000-000000000108", "intro", "What you will do today", {"body": INTRO}))
stmts.append(seg("00000000-0000-4000-8000-000000000101", "reading", "Set up Python", {"body": SETUP}))
stmts.append(seg("00000000-0000-4000-8000-000000000103", "reading", "Notebooks and cells", {"body": NOTEBOOKS}))
stmts.append(seg("00000000-0000-4000-8000-000000000105", "example", "Variables and print()", {"body": FIRST, "on_end": {"type": "open_exercise", "exercise_id": "00000000-0000-4000-8000-0000000000e1"}}))
stmts.append("""update public.lecture_segments set title = 'Check: Python setup' where id = '00000000-0000-4000-8000-000000000102';
update public.lecture_segments set title = 'Check: notebooks' where id = '00000000-0000-4000-8000-000000000104';
update public.lecture_segments set title = 'Lab: print your name' where id = '00000000-0000-4000-8000-000000000106';
update public.lecture_segments set title = 'Exit check' where id = '00000000-0000-4000-8000-000000000107';""")

def question(qid, prompt, options, correct, good, bad, shuffle=False):
    return (f"update public.mcq_questions set prompt = {q(prompt)}, options = {j([{'id': k, 'text': v} for k, v in options])}, "
            f"correct_option_id = '{correct}', explanation_correct = {q(good)}, explanation_incorrect = {q(bad)}, shuffle_options = {str(shuffle).lower()} where id = '{qid}';")
stmts.append(question("00000000-0000-4000-8000-0000000000a1", "Which command prints the version of Python installed on your computer?",
    [("a", "python -v"), ("b", "python --version"), ("c", "python --check")], "b",
    "`python --version` prints the installed version. On macOS and Linux you may need `python3 --version`.",
    "Not quite. `python -v` turns on verbose mode, which traces every import. The command that prints the version is `python --version`."))
stmts.append(question("00000000-0000-4000-8000-0000000000a2", "Which statement about notebook cells is true?",
    [("a", "Each cell can be run on its own, and all cells share the same variables while the kernel is running"),
     ("b", "Every cell has its own separate set of variables"),
     ("c", "Cells run automatically from top to bottom whenever you open the notebook")], "a",
    "Cells share one kernel, so a variable created in one cell can be used by any cell you run afterwards.",
    "Not quite. Cells are separate to run but share the same kernel, so variables carry over. You choose when each cell runs.", True))
stmts.append(question("00000000-0000-4000-8000-0000000000a3", "After running `price = 20` and then `price = price + 5`, what does `print(price)` show?",
    [("a", "25"), ("b", "20"), ("c", "price + 5")], "a",
    "Python works out the right side first using the old value (20 + 5), then stores 25 back under `price`.",
    "Not quite. The second line reads the old value of `price`, adds 5, and stores the answer back, so `price` is now 25."))
stmts.append("""update public.lecture_exercises set title = 'Print your name',
  instructions = 'Create a variable named student_name that holds your name as text. Then print it so your name appears in the output.',
  objective = 'Store text in a variable and show it on screen with print().'
  where id = '00000000-0000-4000-8000-0000000000e1';
update public.exercise_tests set remediation_segment_id = '00000000-0000-4000-8000-000000000105'
  where id = '00000000-0000-4000-8000-0000000000f2';""")

header = """-- Lecture 9 content (real text, no placeholders). Idempotent. Video sections were replaced by written lessons because no
-- lecture recordings exist yet; to add a recording later, set a section's segment_type to 'video' and fill media_url (+ transcript).
-- Hidden test DEFINITIONS are not in this file; they are loaded privately (scripts/load_private_tests.py).
"""
open("database/seed/005_lecture9_content.sql", "w").write(header + "\n".join(stmts) + "\n")
print(len("\n".join(stmts)))
