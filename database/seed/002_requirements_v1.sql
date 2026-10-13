-- Idempotent updates for Requirements v1.0 on the Lecture 9 PLACEHOLDER content.
update public.lecture_exercises set
  max_attempts = null,                               -- §6.2: unlimited practice attempts (abuse limits live in the API)
  hint_penalty_percent = 10,
  hints = '["Start by creating a variable called student_name and give it a text value in quotes.","Use print(student_name) on its own line to show the value.","Make sure the text you print is exactly what student_name holds - print the variable, not a new string."]'::jsonb
where id = '00000000-0000-4000-8000-0000000000e1';

update public.exercise_tests set
  criterion_label = 'Your program prints something',
  remediation = 'Add a print(...) line so your program shows a result.'
where id = '00000000-0000-4000-8000-0000000000f1';
update public.exercise_tests set
  criterion_label = 'student_name holds text',
  remediation = 'Create a variable named student_name and put text in quotes, like student_name = "Aarav".'
where id = '00000000-0000-4000-8000-0000000000f2';
update public.exercise_tests set
  criterion_label = 'The printed text matches student_name',
  remediation = 'Print the variable itself with print(student_name) so the output matches what it stores.'
where id = '00000000-0000-4000-8000-0000000000f3';

-- Transcripts (no captions files yet) for the placeholder videos
update public.lecture_segments set settings = settings || '{"transcript":"PLACEHOLDER transcript. Replace with the real lecture transcript or supply a WebVTT captions_url."}'::jsonb
where lecture_id = '00000000-0000-4000-8000-000000000009' and segment_type = 'video';

-- Teacher assignment for the dev teacher -> dev learners (course: sample)
insert into public.teacher_assignments (teacher_id, learner_id, course_id)
select t.id, l.id, '00000000-0000-4000-8000-000000000001'
from auth.users t join auth.users l on l.email in ('learner1@neuromind.test','learner2@neuromind.test','learner3@neuromind.test')
where t.email = 'teacher@neuromind.test'
on conflict do nothing;
