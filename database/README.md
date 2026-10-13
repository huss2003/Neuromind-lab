# Database
Numbered SQL migrations in `migrations/` are the schema source of truth. Writes by learners go through the API (service role); browser clients only get read access via RLS. `mcq_questions` and `exercise_tests` have no client policies so answer keys and hidden tests never reach the browser.
