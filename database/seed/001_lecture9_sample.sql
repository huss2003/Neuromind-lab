-- Repeatable demo seed: Lecture 9 sample. ALL CONTENT IS PLACEHOLDER (videos, questions, tests)
-- until reviewed by a teacher. Title taken from docs/02-architecture/API_SPEC.md; the
-- curriculum document with official learning objectives was not in the pack.
insert into public.courses (id, slug, title, description, status) values
 ('00000000-0000-4000-8000-000000000001','ai-foundations','NeuroMind AI Course (sample)','Placeholder course shell for the Lecture 9 prototype.','published')
 on conflict (id) do nothing;
insert into public.modules (id, course_id, module_number, title, sort_order, status) values
 ('00000000-0000-4000-8000-000000000002','00000000-0000-4000-8000-000000000001',2,'Python for AI (sample)',2,'published')
 on conflict (id) do nothing;
insert into public.lectures (id, course_id, module_id, lecture_number, title, summary, learning_objectives, duration_seconds, status, content_version, published_at) values
 ('00000000-0000-4000-8000-000000000009','00000000-0000-4000-8000-000000000001','00000000-0000-4000-8000-000000000002',9,
  'Python setup, notebooks and the first program','PLACEHOLDER summary.',
  '["PLACEHOLDER: set up Python","PLACEHOLDER: run a notebook cell","PLACEHOLDER: write and run a first program"]',3600,'published',1,now())
 on conflict (id) do nothing;

insert into public.mcq_questions (id, question_key, question_version, prompt, options, correct_option_id, explanation_correct, explanation_incorrect, status) values
 ('00000000-0000-4000-8000-0000000000a1','00000000-0000-4000-8000-0000000000b1',1,'[Placeholder] Which statement prints text in Python?',
  '[{"id":"a","text":"echo(''Hi'')"},{"id":"b","text":"print(''Hi'')"},{"id":"c","text":"say(''Hi'')"}]','b',
  'print() writes text to the output.','Python uses print() to show text.','published'),
 ('00000000-0000-4000-8000-0000000000a2','00000000-0000-4000-8000-0000000000b2',1,'[Placeholder] What is a notebook cell?',
  '[{"id":"a","text":"A block of code or text you can run on its own"},{"id":"b","text":"A Python package"},{"id":"c","text":"A type of variable"}]','a',
  'A cell is a runnable unit in a notebook.','A cell is a block you can run independently.','published'),
 ('00000000-0000-4000-8000-0000000000a3','00000000-0000-4000-8000-0000000000b3',1,'[Placeholder] Exit check: which symbol assigns a value to a variable?',
  '[{"id":"a","text":"="},{"id":"b","text":"=="},{"id":"c","text":"=>"}]','a',
  '= assigns; == compares.','= is assignment in Python.','published')
 on conflict (id) do nothing;

insert into public.lecture_checkpoints (id, lecture_id, checkpoint_order, checkpoint_type, question_id, required, pass_threshold) values
 ('00000000-0000-4000-8000-0000000000c1','00000000-0000-4000-8000-000000000009',1,'mcq','00000000-0000-4000-8000-0000000000a1',true,null),
 ('00000000-0000-4000-8000-0000000000c2','00000000-0000-4000-8000-000000000009',2,'mcq','00000000-0000-4000-8000-0000000000a2',true,null),
 ('00000000-0000-4000-8000-0000000000c3','00000000-0000-4000-8000-000000000009',3,'exit_check','00000000-0000-4000-8000-0000000000a3',true,100)
 on conflict (id) do nothing;

insert into public.lecture_exercises (id, lecture_id, title, instructions, starter_code, practice_mode, pass_threshold, max_attempts, status) values
 ('00000000-0000-4000-8000-0000000000e1','00000000-0000-4000-8000-000000000009','Print a variable (placeholder)',
  E'Create a variable called student_name and print it.',
  E'student_name = ""\nprint(student_name)\n','both',80,5,'published')
 on conflict (id) do nothing;

-- Hidden tests: the learner API never reads this table.
-- Hidden test definitions are NOT stored in Git. Load them privately with scripts/load_private_tests.py.
insert into public.exercise_tests (id, exercise_id, test_order, test_type, definition, points, is_hidden) values
 ('00000000-0000-4000-8000-0000000000f1','00000000-0000-4000-8000-0000000000e1',1,'stdout','{"description":"Prints a non-empty line","match":"non_empty"}',1,false),
 ('00000000-0000-4000-8000-0000000000f2','00000000-0000-4000-8000-0000000000e1',2,'stdout','{"description":"Defines student_name as a string","check":"variable_is_str","name":"student_name"}',1,false),
 ('00000000-0000-4000-8000-0000000000f3','00000000-0000-4000-8000-0000000000e1',3,'stdout','{"description":"Private test","private":true}',1,true)
 on conflict (id) do nothing;

-- Segments. Practical video links to its exercise explicitly via settings.on_end.
insert into public.lecture_segments (id, lecture_id, segment_order, segment_type, title, media_provider, media_url, duration_seconds, checkpoint_id, exercise_id, settings) values
 ('00000000-0000-4000-8000-000000000101','00000000-0000-4000-8000-000000000009',1,'video','Introduction and first concept (placeholder)','external','https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4',5,null,null,'{}'),
 ('00000000-0000-4000-8000-000000000102','00000000-0000-4000-8000-000000000009',2,'checkpoint','Knowledge check 1',null,null,null,'00000000-0000-4000-8000-0000000000c1',null,'{}'),
 ('00000000-0000-4000-8000-000000000103','00000000-0000-4000-8000-000000000009',3,'video','Second concept (placeholder)','external','https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4',5,null,null,'{}'),
 ('00000000-0000-4000-8000-000000000104','00000000-0000-4000-8000-000000000009',4,'checkpoint','Knowledge check 2',null,null,null,'00000000-0000-4000-8000-0000000000c2',null,'{}'),
 ('00000000-0000-4000-8000-000000000105','00000000-0000-4000-8000-000000000009',5,'video','Practical demonstration (placeholder)','external','https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4',5,null,null,
  '{"on_end":{"type":"open_exercise","exercise_id":"00000000-0000-4000-8000-0000000000e1"}}'),
 ('00000000-0000-4000-8000-000000000106','00000000-0000-4000-8000-000000000009',6,'exercise','Guided exercise',null,null,null,null,'00000000-0000-4000-8000-0000000000e1','{}'),
 ('00000000-0000-4000-8000-000000000107','00000000-0000-4000-8000-000000000009',7,'exit_check','Exit check',null,null,null,'00000000-0000-4000-8000-0000000000c3',null,'{}')
 on conflict (id) do nothing;
