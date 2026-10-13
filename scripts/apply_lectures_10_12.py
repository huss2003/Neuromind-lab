"""Author Lectures 10-12 (real lessons, questions, labs) in the DEV database through the REST API. Idempotent (upserts by id).
Test DEFINITIONS are read from private/exercise_tests_10_12.json (git-ignored) so hidden answers never enter Git.
  backend/.venv/bin/python scripts/apply_lectures_10_12.py"""
import json
import os
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
URL, KEY = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1", os.environ["SUPABASE_SERVICE_ROLE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates,return=minimal"}
NS = uuid.UUID("5a1d3e84-7b6c-4f1e-9a52-0c2d8e4b7f10")
COURSE, MODULE = "00000000-0000-4000-8000-000000000001", "00000000-0000-4000-8000-000000000002"
LEC9 = "00000000-0000-4000-8000-000000000009"
DEFS = json.loads((ROOT / "private" / "exercise_tests_10_12.json").read_text())


def uid(name: str) -> str:
    return str(uuid.uuid5(NS, name))


def opts(*texts: str) -> list[dict]:
    return [{"id": "abc"[i], "text": t} for i, t in enumerate(texts)]


LECTURES = [
    {
        "n": 10, "title": "Numbers, text and f-strings", "prereq": LEC9, "minutes": 35,
        "summary": "Do arithmetic, work with text, and build readable messages from your data with f-strings.",
        "objectives": ["Use + - * / // % and ** and predict the result", "Join, repeat and measure text", "Build a message with an f-string"],
        "intro": "## What you will do today\n\nPython is a calculator that can also handle words. Today you will do arithmetic, work with text, and combine both into a readable message.\n\n- Use the arithmetic operators and know what each one returns\n- Join and repeat text\n- Put values inside a sentence with an f-string\n\nThe lab asks you to build a receipt line from a price and a quantity.",
        "lessons": [
            ("reading", "Numbers and arithmetic", "## Two kinds of number\n\nWhole numbers such as `7` are **integers**. Numbers with a decimal point such as `3.5` are **floats**.\n\n## The operators\n\n- `+` add, `-` subtract, `*` multiply\n- `/` divide, always giving a float: `7 / 2` is `3.5`\n- `//` divide and round down to a whole number: `7 // 2` is `3`\n- `%` the remainder: `7 % 2` is `1`\n- `**` power: `2 ** 3` is `8`\n\nMultiplication and division happen before addition and subtraction, as in maths. Use brackets to be explicit: `(2 + 3) * 4` is `20`.\n\n```\nprice = 12\nquantity = 5\ntotal = price * quantity\nprint(total)\n```\n\nThis prints `60`."),
            ("reading", "Text and f-strings", "## Strings\n\nText in quotes is a **string**. You can use single or double quotes, as long as they match.\n\n- `\"ab\" + \"cd\"` joins them: `abcd`\n- `\"ab\" * 3` repeats: `ababab`\n- `len(\"hello\")` counts characters: `5`\n- `\"tea\".upper()` gives `TEA`\n\n## f-strings\n\nPut an `f` before the opening quote and write variable names inside curly brackets. Python replaces each one with its value.\n\n```\nitem = \"tea\"\nprice = 3\nprint(f\"{item} costs {price}\")\n```\n\nThis prints `tea costs 3`. You can even calculate inside the brackets: `f\"{price * 2}\"` gives `6`.\n\nWithout the `f`, Python prints the brackets exactly as written."),
        ],
        "example": ("A receipt line", "## Putting it together\n\nA shop sells 5 notebooks at 12 each. We want one line of output that says the total.\n\n```\nprice = 12\nquantity = 5\ntotal = price * quantity\nmessage = f\"Total: {total}\"\nprint(message)\n```\n\nOutput:\n\n```\nTotal: 60\n```\n\n## Why a variable for the message\n\nStoring the sentence in `message` first lets you print it, save it, or change it later without repeating the calculation.\n\n## Common mistakes\n\n- Forgetting the `f` prints `Total: {total}` literally.\n- Using `\"Total: \" + total` fails, because you cannot add text and a number. Use an f-string or `str(total)`.\n- `/` always gives a float, so `10 / 2` is `5.0`, not `5`."),
        "checks": [
            ("What does `7 // 2` evaluate to?", opts("3.5", "3", "4"), "b", "`//` is floor division: it divides and drops everything after the decimal point, so `7 // 2` is 3. Use `/` if you want 3.5.", "Not quite. `/` would give 3.5, but `//` rounds the result down to a whole number, giving 3.", False),
            ("If item is \"tea\" and price is 3, what does f\"{item} costs {price}\" produce?", opts("tea costs 3", "{item} costs {price}", "\"tea\" costs \"3\""), "a", "An f-string replaces each name in curly brackets with that variable's value, so you get tea costs 3.", "Not quite. The curly brackets are replaced by the values of the variables. They only appear literally when the f is missing.", True),
        ],
        "exit": ("What does \"ab\" * 3 give?", opts("ababab", "ab3", "An error"), "a", "Multiplying text by a whole number repeats it, so \"ab\" * 3 is ababab.", "Not quite. Text can be repeated with *, so \"ab\" * 3 gives ababab. It is joining text with a number using + that causes an error."),
        "lab": {
            "title": "Build a receipt line", "objective": "Calculate a total and report it in a sentence built with an f-string.",
            "instructions": "The variables price and quantity are already set. Create total as price times quantity. Create message as an f-string that reads Total: followed by the total. Print message.",
            "constraints": "Keep the variable names total and message. Use an f-string for message. Print only message.",
            "starter": "price = 12\nquantity = 5\n\n# 1. Create total: the price multiplied by the quantity\n# 2. Create message: an f-string that says Total: and then the total\n# 3. Print message\n",
            "examples": [{"description": "A different shop", "code": "price = 4\nquantity = 3\ntotal = price * quantity\nmessage = f\"Total: {total}\"\nprint(message)", "expected_output": "Total: 12"}],
            "criteria": ["Your program prints a line of text", "total equals price times quantity", "The printed text is exactly Total: 60"],
            "hints": ["Multiply the two given variables: total = price * quantity.", "Start the f-string with f and put the variable in curly brackets, like f\"Total: {total}\".", "Print the variable message with print(message). Do not put quotes around message."],
            "tests": [("l10-t1", "Your program prints something", "Add a print(...) line so your program shows a result.", "Print output with print()", "example"),
                      ("l10-t2", "total equals price times quantity", "Create total with total = price * quantity.", "Arithmetic with variables", "reading1"),
                      ("l10-t3", "", "Check the message: it must read Total: followed by the total, built with an f-string and printed.", "Build text with f-strings", "reading2")],
        },
    },
    {
        "n": 11, "title": "Making decisions with if", "prereq": "10", "minutes": 35,
        "summary": "Compare values, combine conditions, and make your program choose what to do with if, elif and else.",
        "objectives": ["Write comparisons that give True or False", "Combine conditions with and, or and not", "Choose between actions with if, elif and else"],
        "intro": "## What you will do today\n\nUp to now your programs ran every line in order. Today they start to make choices.\n\n- Compare values and read the True or False answer\n- Combine conditions with `and`, `or` and `not`\n- Run different code with `if`, `elif` and `else`\n\nIn the lab your program will decide whether a score is a pass.",
        "lessons": [
            ("reading", "True, False and comparisons", "## Booleans\n\nPython has two truth values, `True` and `False`. A comparison produces one.\n\n- `==` equal, `!=` not equal\n- `<` less than, `>` greater than, `<=` and `>=` including equal\n\n`5 > 3` is `True`. `5 == 3` is `False`.\n\nRemember: one `=` stores a value; two `==` ask whether two values are equal.\n\n## Combining conditions\n\n- `and` is True only when both sides are True\n- `or` is True when at least one side is True\n- `not` flips True and False\n\n```\nage = 20\nprint(age >= 18 and age < 65)\n```\n\nThis prints `True`."),
            ("reading", "if, elif and else", "## Making a choice\n\nAn `if` statement runs its indented block only when the condition is True.\n\n```\nscore = 72\nif score >= 50:\n    print(\"pass\")\nelse:\n    print(\"fail\")\n```\n\nThree details matter:\n\n- The line ends with a colon `:`\n- The block underneath is **indented** (four spaces). Indentation is how Python knows what belongs to the `if`\n- `else` runs when the condition was False\n\n## More than two outcomes\n\nUse `elif` (short for else if) for extra conditions. Python checks them from the top and runs the first one that is True.\n\n```\nif score >= 80:\n    print(\"distinction\")\nelif score >= 50:\n    print(\"pass\")\nelse:\n    print(\"fail\")\n```"),
        ],
        "example": ("Storing a decision", "## A decision you can keep\n\nOften you want to remember the outcome, not just print it. Store it in a variable:\n\n```\nscore = 72\nif score >= 50:\n    grade = \"pass\"\nelse:\n    grade = \"fail\"\nprint(grade)\n```\n\nOutput:\n\n```\npass\n```\n\n## Reading the program\n\n1. `score` is 72.\n2. `72 >= 50` is True, so the first block runs and `grade` becomes `\"pass\"`.\n3. The `else` block is skipped.\n4. `print(grade)` shows `pass`.\n\n## Common mistakes\n\n- A missing colon causes a `SyntaxError`.\n- Blocks that are not indented cause an `IndentationError`.\n- Writing `if score = 50` (one `=`) is an error. Use `==` to compare."),
        "checks": [
            ("What does 5 > 3 and 2 > 4 evaluate to?", opts("True", "False", "3"), "b", "`and` needs both sides to be True. 5 > 3 is True but 2 > 4 is False, so the whole expression is False.", "Not quite. 5 > 3 is True, but 2 > 4 is False, and `and` is only True when both sides are True.", False),
            ("Which line correctly starts an if block?", opts("if score >= 50:", "if score >= 50", "if (score >= 50) then"), "a", "An if line ends with a colon, and the block that follows is indented.", "Not quite. Python needs the colon at the end of the line. There is no `then` in Python.", True),
        ],
        "exit": ("x is 10. The branches print big when x > 20, medium when x > 5 (checked second), and small otherwise. What is printed?", opts("big", "medium", "small"), "b", "x > 20 is False, so Python moves to elif. x > 5 is True, so it prints medium and skips the rest.", "Not quite. 10 is not above 20, so the first branch is skipped. 10 is above 5, so the elif branch runs and prints medium."),
        "lab": {
            "title": "Pass or fail", "objective": "Use if and else to store a decision in a variable and print it.",
            "instructions": "The variable score is already set. Create a variable named grade that is \"pass\" when score is 50 or more, and \"fail\" otherwise. Then print grade.",
            "constraints": "Use if and else. Keep the variable names score and grade. Print only grade.",
            "starter": "score = 72\n\n# Create grade: \"pass\" if score is 50 or more, otherwise \"fail\"\n# Print grade\n",
            "examples": [{"description": "A lower score", "code": "score = 30\nif score >= 50:\n    grade = \"pass\"\nelse:\n    grade = \"fail\"\nprint(grade)", "expected_output": "fail"}],
            "criteria": ["Your program prints a line of text", "grade is the right word for the score", "What you print matches grade"],
            "hints": ["Start with if score >= 50: and indent the next line by four spaces.", "Inside the if block write grade = \"pass\". Inside else: write grade = \"fail\".", "Print the variable on its own line at the end, with no indentation: print(grade)."],
            "tests": [("l11-t1", "Your program prints something", "Add a print(...) line so your program shows a result.", "Print output with print()", "example"),
                      ("l11-t2", "grade is the right word for the score", "Use an if/else so grade is \"pass\" when score >= 50.", "Choose with if and else", "reading2"),
                      ("l11-t3", "", "Print the variable grade so the output matches what it stores.", "Print output with print()", "example")],
        },
    },
    {
        "n": 12, "title": "Lists and loops", "prereq": "11", "minutes": 40,
        "summary": "Keep several values in a list and use a for loop to work through them one at a time.",
        "objectives": ["Create a list and read items by position", "Repeat an action for every item with a for loop", "Add values up with an accumulator variable"],
        "intro": "## What you will do today\n\nReal data comes in groups: scores, prices, names. Today you will keep a group of values in a list and process it with a loop.\n\n- Create lists and read items by position\n- Use a `for` loop to visit every item\n- Add up values with a running total\n\nIn the lab you will add up a list of numbers with a loop.",
        "lessons": [
            ("reading", "Lists", "## A list holds many values\n\nA **list** keeps values in order, between square brackets and separated by commas.\n\n```\nnumbers = [4, 8, 15]\n```\n\n## Positions start at zero\n\nEach item has a position called an **index**, and the first index is `0`.\n\n- `numbers[0]` is `4`\n- `numbers[1]` is `8`\n- `numbers[-1]` is the last item, `15`\n\n## Useful tools\n\n- `len(numbers)` is how many items: `3`\n- `numbers.append(16)` adds an item at the end\n- Asking for a position that does not exist, such as `numbers[5]`, causes an `IndexError`."),
            ("reading", "for loops", "## Repeating an action\n\nA `for` loop runs its indented block once for each item in a list. On each pass, the loop variable holds the current item.\n\n```\nfor n in [3, 6, 9]:\n    print(n)\n```\n\nThis prints 3, then 6, then 9.\n\n## Counting with range\n\n`range(3)` produces `0, 1, 2`, which is handy when you just need to repeat something three times:\n\n```\nfor i in range(3):\n    print(\"hello\")\n```\n\n## Keeping a running total\n\nCreate a variable before the loop and update it inside:\n\n```\ntotal = 0\nfor n in [3, 6, 9]:\n    total = total + n\nprint(total)\n```\n\nThis prints `18`. The variable that collects the answer is often called an **accumulator**."),
        ],
        "example": ("Adding up a list", "## Summing a list of scores\n\n```\nscores = [70, 85, 90]\ntotal = 0\nfor s in scores:\n    total = total + s\nprint(total)\n```\n\nOutput:\n\n```\n245\n```\n\n## Following it step by step\n\n| pass | s | total after |\n|---|---|---|\n\nWork through it on paper: `total` starts at 0. After the first pass it is 70, after the second 155, after the third 245.\n\n## Common mistakes\n\n- Setting `total = 0` inside the loop resets it every time. Set it once, before the loop.\n- Forgetting to indent the line inside the loop means it runs only once, after the loop ends.\n- Printing inside the loop prints every running total; print after the loop for just the answer."),
        "checks": [
            ("numbers = [4, 8, 15]. What is numbers[1]?", opts("4", "8", "15"), "b", "Positions start at zero, so numbers[0] is 4 and numbers[1] is 8.", "Not quite. Counting starts at 0: numbers[0] is 4, numbers[1] is 8 and numbers[2] is 15.", False),
            ("How many times does the body of `for n in [3, 6, 9]:` run?", opts("Three times, once for each item", "Nine times", "Once"), "a", "A for loop runs its body once per item. The list has three items, so the body runs three times.", "Not quite. The body runs once for each item in the list, and this list has three items.", True),
        ],
        "exit": ("total starts at 0. The loop is for n in [1, 2, 3]: total = total + n. What is total afterwards?", opts("3", "6", "123"), "b", "Each pass adds the current item: 0 + 1 + 2 + 3 gives 6.", "Not quite. The loop adds each item to the running total: 0 + 1 = 1, then 1 + 2 = 3, then 3 + 3 = 6."),
        "lab": {
            "title": "Add up a list", "objective": "Use a for loop and a running total to add up every number in a list.",
            "instructions": "The list numbers is already set. Create total as 0, use a for loop to add every item of numbers to it, then print total.",
            "constraints": "Use a for loop. Keep the variable names numbers and total. Print only total, once, after the loop.",
            "starter": "numbers = [3, 1, 4, 1, 5]\n\n# Create total, starting at 0\n# Use a for loop to add every number to total\n# Print total\n",
            "examples": [{"description": "A shorter list", "code": "numbers = [2, 2, 2]\ntotal = 0\nfor n in numbers:\n    total = total + n\nprint(total)", "expected_output": "6"}],
            "criteria": ["Your program prints a line of text", "total holds the sum of the numbers", "The printed text is exactly 14"],
            "hints": ["Create the variable before the loop: total = 0.", "Write for n in numbers: and, on the next line indented, total = total + n.", "Put print(total) after the loop, at the left margin, so it prints once."],
            "tests": [("l12-t1", "Your program prints something", "Add a print(...) line so your program shows a result.", "Print output with print()", "example"),
                      ("l12-t2", "total holds the sum of the numbers", "Start total at 0 and add each number inside the loop.", "Accumulate with a loop", "reading2"),
                      ("l12-t3", "", "Print total once after the loop so the output is the sum.", "Accumulate with a loop", "example")],
        },
    },
]


def put(c: httpx.Client, table: str, rows: list[dict] | dict) -> None:
    r = c.post(f"{URL}/{table}", headers=H, json=rows)
    if r.status_code >= 300:
        raise SystemExit(f"{table}: {r.status_code} {r.text[:300]}")


def main() -> None:
    ids: dict[int, str] = {9: LEC9}
    with httpx.Client(timeout=40) as c:
        for L in LECTURES:
            n = L["n"]
            lid = uid(f"lecture{n}")
            ids[n] = lid
            prereq = [LEC9] if L["prereq"] == LEC9 else [ids[int(L["prereq"]) - 1 + 1 - 1 + 0] if False else uid(f"lecture{L['prereq']}")]
            seg = lambda k: uid(f"l{n}-seg{k}")  # noqa: E731
            put(c, "lectures", {"id": lid, "course_id": COURSE, "module_id": MODULE, "lecture_number": n, "title": L["title"], "summary": L["summary"],
                                "learning_objectives": L["objectives"], "duration_seconds": L["minutes"] * 60, "status": "published", "content_version": 1,
                                "published_at": "2026-10-13T00:00:00Z", "prerequisites": prereq})
            # questions and checkpoints
            qs = []
            for i, (prompt, options, correct, good, bad, shuffle) in enumerate(L["checks"] + [(*L["exit"], False)], start=1):
                qs.append({"id": uid(f"l{n}-q{i}"), "question_key": uid(f"l{n}-qk{i}"), "question_version": 1, "prompt": prompt, "options": options, "correct_option_id": correct,
                           "explanation_correct": good, "explanation_incorrect": bad, "points": 1, "status": "published", "shuffle_options": shuffle, "reveal_policy": "always"})
            put(c, "mcq_questions", qs)
            put(c, "lecture_checkpoints", [
                {"id": uid(f"l{n}-cp{i}"), "lecture_id": lid, "checkpoint_order": i, "checkpoint_type": "exit_check" if i == 3 else "mcq", "question_id": uid(f"l{n}-q{i}"),
                 "required": True, "pass_threshold": 100 if i == 3 else None, "settings": {}} for i in (1, 2, 3)])
            lab = L["lab"]
            ex = uid(f"l{n}-ex")
            put(c, "lecture_exercises", {"id": ex, "lecture_id": lid, "title": lab["title"], "instructions": lab["instructions"], "language": "python", "starter_code": lab["starter"],
                                         "practice_mode": "both", "pass_threshold": 80, "max_attempts": None, "status": "published", "test_suite_version": 1,
                                         "hints": lab["hints"], "hint_penalty_percent": 10, "objective": lab["objective"], "constraints": lab["constraints"],
                                         "visible_examples": lab["examples"], "success_criteria": lab["criteria"]})
            ex_title, ex_body = L["example"]
            segs = [
                (1, "intro", "What you will do today", {"body": L["intro"]}, None, None),
                (2, "reading", L["lessons"][0][1], {"body": L["lessons"][0][2]}, None, None),
                (3, "checkpoint", f"Check: {L['lessons'][0][1].lower()}", {}, uid(f"l{n}-cp1"), None),
                (4, "reading", L["lessons"][1][1], {"body": L["lessons"][1][2]}, None, None),
                (5, "checkpoint", f"Check: {L['lessons'][1][1].lower()}", {}, uid(f"l{n}-cp2"), None),
                (6, "example", ex_title, {"body": ex_body, "on_end": {"type": "open_exercise", "exercise_id": ex}}, None, None),
                (7, "exercise", f"Lab: {lab['title'].lower()}", {}, None, ex),
                (8, "exit_check", "Exit check", {}, uid(f"l{n}-cp3"), None),
            ]
            put(c, "lecture_segments", [{"id": seg(k), "lecture_id": lid, "segment_order": k, "segment_type": t, "title": title, "is_required": True, "settings": st,
                                         "checkpoint_id": cp, "exercise_id": e} for k, t, title, st, cp, e in segs])
            remed = {"example": seg(6), "reading1": seg(2), "reading2": seg(4)}
            put(c, "exercise_tests", [
                {"id": uid(f"l{n}-test{i}"), "exercise_id": ex, "test_order": i, "test_type": "stdout", "definition": DEFS[key], "points": 1, "is_hidden": i == 3,
                 "criterion_label": label or None, "remediation": rem, "objective": obj, "remediation_segment_id": remed[where]}
                for i, (key, label, rem, obj, where) in enumerate(lab["tests"], start=1)])
            print(f"ok lecture {n}: {L['title']}")


if __name__ == "__main__":
    main()
