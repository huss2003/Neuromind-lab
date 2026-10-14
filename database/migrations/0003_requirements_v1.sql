-- 0003: Requirements v1.0 — evidence fields, hints/remediation, best-score support, teacher assignment,
-- teacher feedback, saved drafts, grant hardening. Additive; no destructive changes.

-- §6.3 evidence + GRD-008 versions on official attempts
alter table public.lab_submissions
  add column content_version int,
  add column grader_version text,
  add column test_suite_version int,
  add column max_score numeric not null default 100,
  add column pass_threshold numeric,
  add column raw_score numeric,
  add column hints_used int not null default 0,
  add column hint_penalty numeric not null default 0,
  add column criteria_results jsonb not null default '[]',
  add column correlation_id text,
  add column started_at timestamptz,
  add column finished_at timestamptz;

alter table public.checkpoint_attempts
  add column question_version int,
  add column content_version int;

-- Exercise: hints (ordered, learner-visible), penalty policy, suite version
alter table public.lecture_exercises
  add column test_suite_version int not null default 1,
  add column hints jsonb not null default '[]',
  add column hint_penalty_percent numeric not null default 10 check (hint_penalty_percent between 0 and 100);

-- Per-criterion safe labels and remediation (server-only table; text is only shown after a failure)
alter table public.exercise_tests
  add column criterion_label text,
  add column remediation text;

-- Hint reveals are recorded per attempt number so the penalty applies to the current attempt only
create table public.exercise_hint_reveals (
  id uuid primary key default gen_random_uuid(),
  learner_id uuid not null references public.profiles(id) on delete cascade,
  exercise_id uuid not null references public.lecture_exercises(id) on delete cascade,
  hint_index int not null check (hint_index >= 0),
  attempt_number int not null check (attempt_number >= 1),
  revealed_at timestamptz not null default now(),
  unique (learner_id, exercise_id, attempt_number, hint_index)
);

-- §7.1 saving/restoring work
create table public.lab_drafts (
  id uuid primary key default gen_random_uuid(),
  learner_id uuid not null references public.profiles(id) on delete cascade,
  exercise_id uuid not null references public.lecture_exercises(id) on delete cascade,
  source_code text not null check (octet_length(source_code) <= 50000),
  updated_at timestamptz not null default now(),
  unique (learner_id, exercise_id)
);

-- §3/§9 teacher scope: assigned learners per course; revocable
create table public.teacher_assignments (
  id uuid primary key default gen_random_uuid(),
  teacher_id uuid not null references public.profiles(id) on delete cascade,
  learner_id uuid not null references public.profiles(id) on delete cascade,
  course_id uuid not null references public.courses(id) on delete cascade,
  created_at timestamptz not null default now(),
  revoked_at timestamptz,
  unique (teacher_id, learner_id, course_id)
);
create index teacher_assignments_teacher_idx on public.teacher_assignments(teacher_id) where revoked_at is null;

-- §9.2 teacher feedback: never alters official scores
create table public.teacher_feedback (
  id uuid primary key default gen_random_uuid(),
  learner_id uuid not null references public.profiles(id) on delete cascade,
  author_id uuid not null references public.profiles(id),
  lecture_id uuid references public.lectures(id),
  submission_id uuid references public.lab_submissions(id),
  body text not null check (char_length(body) between 1 and 2000),
  published boolean not null default false,
  published_at timestamptz,
  content_version int,
  created_at timestamptz not null default now()
);
create index teacher_feedback_learner_idx on public.teacher_feedback(learner_id, created_at desc);

alter table public.exercise_hint_reveals enable row level security;
alter table public.lab_drafts enable row level security;
alter table public.teacher_assignments enable row level security;
alter table public.teacher_feedback enable row level security;

create policy hints_select_own on public.exercise_hint_reveals for select to authenticated using (learner_id = (select auth.uid()));
create policy drafts_select_own on public.lab_drafts for select to authenticated using (learner_id = (select auth.uid()));
create policy assignments_select_own on public.teacher_assignments for select to authenticated using (teacher_id = (select auth.uid()));
create policy feedback_select_published_own on public.teacher_feedback for select to authenticated
  using (learner_id = (select auth.uid()) and published);

-- Defence in depth: browsers never need table writes (all writes go through the API with the service role),
-- and anonymous visitors need no table access at all. RLS remains the primary control.
revoke all on all tables in schema public from anon;
revoke insert, update, delete, truncate, references, trigger on all tables in schema public from authenticated;
alter default privileges for role postgres in schema public revoke all on tables from anon;
alter default privileges for role postgres in schema public revoke insert, update, delete, truncate, references, trigger on tables from authenticated;
