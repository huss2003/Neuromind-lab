# Course document change notes (for AI_Creator_Program_104Hours_FIXED_v2.docx)

The practical labs follow the course document. These are the places where the platform's labs differ from the document, so the document can be updated to match (owner decision 2026-10-16: the document changes, not the platform).

## 1. Public and AI APIs are predefined
Any lab that asks the learner to "call a public API", "use an AI API" or "build a chatbot/RAG with a model" uses the **predefined practice API** instead of a real service:
- Base URL `https://api.neuromind.lab/v1`, test key `nm-test-key-123` (sent as `Authorization: Bearer …`).
- Endpoints (full table in PRACTICAL_LABS_SPEC.md §6): `GET /weather`, `GET /books`, `GET /news/headlines`, `GET /secure/profile`, `GET /flaky`, `GET /search`, `POST /chat`, `POST /generate`, `POST /sentiment`, `POST /entities`, `POST /embeddings`, `POST /ocr`, `POST /vision/classify`, `POST /vision/detect`, `POST /vision/ask`; Python helpers `tokenizer`, `VectorIndex`, `multimodal`.
- It works in the browser and in the grader, is deterministic, costs nothing, needs no account, and never reaches the internet. Any other host raises a connection error.
Document wording to change: replace references to real weather, news, OpenAI, Gemini, Hugging Face Inference and similar services with "the NeuroMind practice API (details in the lab)".

## 2. Lectures 9 to 12
The old platform labs for these lectures were replaced with the document's practical projects (`hello.py` self-introduction, calculator with f-strings, grade-decider, shopping-list loops). No document change.

## 3. Single-file adaptations
- Lecture 13 (loops): the document's infinite-loop demonstration is a `while` loop whose counter never changes; the learner fixes it so both loops print the same total. The checker stops a program that runs too long and explains that this is an infinite loop (it cannot wait for a person to interrupt the program).
- Lecture 15 (tuples): "try to change a tuple and watch the error" is checked by catching the `TypeError` inside `try`/`except` and printing a message, instead of letting the program crash.
- Lecture 18 (debugging): the bug log is the list `bug_log` inside the same `.py` file (four short texts), not a separate document.
- Lecture 19 (modules): the two-file project (`helpers.py` plus `main.py`) is one file with two marked sections, because a lab has one editor.

## 4. Written, upload and exam labs
- Design/reflection tasks are submitted as text and marked by the teacher from a rubric shown in the lab.
- Deployment and presentation lectures (84, 103, 104) are a checklist plus a link; the teacher marks them.
- Exam lectures (87 to 98) are auto-marked question sets (pass mark in the lab).
