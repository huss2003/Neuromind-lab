-- Idempotent updates for Flow v1.0 on the PLACEHOLDER Lecture 9 content.
update public.lecture_exercises set
  objective = 'Create a text variable and print it to the screen.',
  constraints = 'Use a variable named student_name. Use print() once. No input() or imports are needed.',
  visible_examples = '[{"description":"Example","code":"student_name = \"Aarav\"\nprint(student_name)","expected_output":"Aarav"}]'::jsonb,
  success_criteria = '["Your program prints a line of text","student_name holds text","What you print matches student_name"]'::jsonb
where id = '00000000-0000-4000-8000-0000000000e1';

update public.exercise_tests set objective = 'Print output with print()', remediation_segment_id = '00000000-0000-4000-8000-000000000105'
  where id in ('00000000-0000-4000-8000-0000000000f1','00000000-0000-4000-8000-0000000000f3');
update public.exercise_tests set objective = 'Store text in a variable', remediation_segment_id = '00000000-0000-4000-8000-000000000103'
  where id = '00000000-0000-4000-8000-0000000000f2';

-- Intro section (order 1) using the new text section type; shift the others by one in two steps (unique constraint).
do $$
begin
  if not exists (select 1 from public.lecture_segments where id = '00000000-0000-4000-8000-000000000108') then
    update public.lecture_segments set segment_order = segment_order + 100 where lecture_id = '00000000-0000-4000-8000-000000000009';
    update public.lecture_segments set segment_order = segment_order - 99 where lecture_id = '00000000-0000-4000-8000-000000000009';
    insert into public.lecture_segments (id, lecture_id, segment_order, segment_type, title, is_required, settings)
    values ('00000000-0000-4000-8000-000000000108','00000000-0000-4000-8000-000000000009',1,'intro','Introduction: what you will do today',true,
      '{"body":"PLACEHOLDER introduction. In this lecture you will set up Python, run a notebook cell and write your first program. By the end you will be able to print a value and explain what the program did."}'::jsonb);
  end if;
end $$;

insert into public.enrollments (learner_id, course_id)
select u.id, '00000000-0000-4000-8000-000000000001' from auth.users u
where u.email in ('learner1@neuromind.test','learner2@neuromind.test','learner3@neuromind.test')
on conflict do nothing;
