-- Run against a DEV project only (e.g. Supabase SQL editor / execute_sql). Always rolls back via the final RAISE.
-- Expected result string:
-- u2 sees u1 sessions: 0; u2 sees u1 submissions: 0; u2 profiles visible: 1; segments visible: 7;
-- mcq rows visible: 0; tests rows visible: 0; self role update rows: 0; attempt insert denied;
do $$
declare
  u1 uuid := gen_random_uuid(); u2 uuid := gen_random_uuid();
  n int; res text := '';
begin
  insert into auth.users (id, instance_id, aud, role, email) values
    (u1,'00000000-0000-0000-0000-000000000000','authenticated','authenticated','rls1@test.invalid'),
    (u2,'00000000-0000-0000-0000-000000000000','authenticated','authenticated','rls2@test.invalid');
  insert into lecture_sessions (learner_id, lecture_id) values (u1,'00000000-0000-4000-8000-000000000009');
  insert into lab_submissions (learner_id, exercise_id, submission_number, source_code) values (u1,'00000000-0000-4000-8000-0000000000e1',1,'print(1)');
  perform set_config('request.jwt.claims', json_build_object('sub',u2,'role','authenticated')::text, true);
  set local role authenticated;
  select count(*) into n from lecture_sessions; res := res || 'u2 sees u1 sessions: '||n||'; ';
  select count(*) into n from lab_submissions; res := res || 'u2 sees u1 submissions: '||n||'; ';
  select count(*) into n from profiles; res := res || 'u2 profiles visible: '||n||'; ';
  select count(*) into n from lecture_segments; res := res || 'segments visible: '||n||'; ';
  select count(*) into n from mcq_questions; res := res || 'mcq rows visible: '||n||'; ';
  select count(*) into n from exercise_tests; res := res || 'tests rows visible: '||n||'; ';
  update profiles set role='admin' where id=u2; get diagnostics n = row_count; res := res || 'self role update rows: '||n||'; ';
  begin
    insert into checkpoint_attempts (learner_id, checkpoint_id, question_id, selected_option_id, is_correct, score, idempotency_key)
    values (u2,'00000000-0000-4000-8000-0000000000c1','00000000-0000-4000-8000-0000000000a1','b',true,1,gen_random_uuid());
    res := res || 'INSERT ATTEMPT ALLOWED (BAD); ';
  exception when others then res := res || 'attempt insert denied; '; end;
  raise exception 'RLS_RESULT: %', res;
end $$;
