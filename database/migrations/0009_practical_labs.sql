-- 0009: Practical Labs (see docs/01-product/PRACTICAL_LABS_SPEC.md). Additive. All new tables are API-only (RLS on, no policies).

-- Lab kinds, pass/fail scoring, libraries, data files, limits, rubric/checklist for teacher-marked kinds, hint cap.
alter table public.lecture_exercises
  add column lab_kind text not null default 'code' check (lab_kind in ('code','quiz','written','upload')),
  add column scoring text not null default 'score' check (scoring in ('score','pass_fail')),
  add column packages jsonb not null default '[]',
  add column assets jsonb not null default '[]',
  add column limits jsonb not null default '{}',
  add column rubric jsonb not null default '[]',
  add column checklist jsonb not null default '[]',
  add column hints_max int not null default 3 check (hints_max between 0 and 10);

-- Hints are counted per "cycle"; Redo starts a new cycle (keeps the attempt history).
alter table public.exercise_hint_reveals add column cycle int not null default 1 check (cycle >= 1);
do $$
declare c text;
begin
  select conname into c from pg_constraint
   where conrelid = 'public.exercise_hint_reveals'::regclass and contype = 'u';
  if c is not null then execute format('alter table public.exercise_hint_reveals drop constraint %I', c); end if;
end $$;
alter table public.exercise_hint_reveals add constraint exercise_hint_reveals_unique unique (learner_id, exercise_id, cycle, attempt_number, hint_index);

create table public.lab_hint_state (
  learner_id uuid not null references public.profiles(id) on delete cascade,
  exercise_id uuid not null references public.lecture_exercises(id) on delete cascade,
  cycle int not null default 1 check (cycle >= 1),
  redo_count int not null default 0,
  updated_at timestamptz not null default now(),
  primary key (learner_id, exercise_id)
);

-- Quiz labs: questions live here (correct_option_id is server-only, like mcq_questions).
create table public.lab_questions (
  id uuid primary key default gen_random_uuid(),
  exercise_id uuid not null references public.lecture_exercises(id) on delete cascade,
  question_order int not null,
  prompt text not null,
  options jsonb not null,
  correct_option_id text not null,
  explanation text not null default '',
  points numeric(6,2) not null default 1,
  unique (exercise_id, question_order)
);

-- Written/upload kinds: the learner's answers and the teacher's review. 'submitted' = awaiting review.
alter table public.lab_submissions add column answers jsonb;
alter table public.lab_submissions drop constraint lab_submissions_status_check;
alter table public.lab_submissions add constraint lab_submissions_status_check
  check (status in ('queued','running','passed','failed','timeout','error','runtime_error','expired','cancelled','submitted'));

create table public.lab_reviews (
  id uuid primary key default gen_random_uuid(),
  submission_id uuid not null unique references public.lab_submissions(id) on delete cascade,
  reviewer_id uuid references public.profiles(id) on delete set null,
  scores jsonb not null default '[]',
  passed boolean not null,
  feedback text not null default '' check (char_length(feedback) <= 4000),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index lab_reviews_reviewer_idx on public.lab_reviews(reviewer_id, created_at desc);
create index lab_submissions_submitted_idx on public.lab_submissions(status, created_at) where status = 'submitted';

alter table public.lab_hint_state enable row level security;
alter table public.lab_questions enable row level security;
alter table public.lab_reviews enable row level security;
revoke all on public.lab_hint_state, public.lab_questions, public.lab_reviews from anon, authenticated;
