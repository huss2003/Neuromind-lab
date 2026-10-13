-- 0001 initial schema (see docs/02-architecture/DATA_MODEL_AND_DATABASE_SCHEMA.md)
create extension if not exists pgcrypto;

create or replace function public.set_updated_at() returns trigger
language plpgsql set search_path = '' as $$
begin new.updated_at = now(); return new; end $$;

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null default '',
  role text not null default 'learner' check (role in ('learner','teacher','admin')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.courses (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  title text not null,
  description text not null default '',
  status text not null default 'draft' check (status in ('draft','published','archived')),
  created_by uuid references public.profiles(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index courses_status_created_idx on public.courses(status, created_at);

create table public.modules (
  id uuid primary key default gen_random_uuid(),
  course_id uuid not null references public.courses(id) on delete cascade,
  module_number int not null,
  title text not null,
  description text not null default '',
  sort_order int not null,
  status text not null default 'draft' check (status in ('draft','published','archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (course_id, module_number),
  unique (course_id, sort_order)
);

create table public.lectures (
  id uuid primary key default gen_random_uuid(),
  course_id uuid not null references public.courses(id) on delete cascade,
  module_id uuid not null references public.modules(id) on delete cascade,
  lecture_number int not null,
  title text not null,
  summary text not null default '',
  learning_objectives jsonb not null default '[]',
  duration_seconds int,
  status text not null default 'draft' check (status in ('draft','published','archived')),
  content_version int not null default 1,
  published_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (course_id, lecture_number)
);
create index lectures_module_status_idx on public.lectures(module_id, status);

create table public.mcq_questions (
  id uuid primary key default gen_random_uuid(),
  question_key uuid not null default gen_random_uuid(),
  question_version int not null default 1,
  prompt text not null,
  options jsonb not null,
  correct_option_id text not null, -- server-only
  explanation_correct text not null default '',
  explanation_incorrect text,
  points numeric(6,2) not null default 1,
  status text not null default 'draft' check (status in ('draft','published','archived')),
  created_by uuid references public.profiles(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (question_key, question_version)
);

create table public.lecture_checkpoints (
  id uuid primary key default gen_random_uuid(),
  lecture_id uuid not null references public.lectures(id) on delete cascade,
  checkpoint_order int not null,
  checkpoint_type text not null check (checkpoint_type in ('mcq','exit_check')),
  question_id uuid not null references public.mcq_questions(id),
  required boolean not null default true,
  pass_threshold numeric,
  settings jsonb not null default '{}',
  created_at timestamptz not null default now(),
  unique (lecture_id, checkpoint_order)
);

create table public.lecture_exercises (
  id uuid primary key default gen_random_uuid(),
  lecture_id uuid not null references public.lectures(id) on delete cascade,
  title text not null,
  instructions text not null default '',
  language text not null default 'python' check (language = 'python'),
  starter_code text not null default '',
  practice_mode text not null default 'both' check (practice_mode in ('pyodide','server','both')),
  pass_threshold numeric not null default 80,
  max_attempts int,
  status text not null default 'draft' check (status in ('draft','published','archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index lecture_exercises_lecture_status_idx on public.lecture_exercises(lecture_id, status);

create table public.exercise_tests (
  id uuid primary key default gen_random_uuid(),
  exercise_id uuid not null references public.lecture_exercises(id) on delete cascade,
  test_order int not null,
  test_type text not null check (test_type in ('stdout','function','unit')),
  definition jsonb not null,
  points numeric not null default 1,
  is_hidden boolean not null default false,
  created_at timestamptz not null default now(),
  unique (exercise_id, test_order)
);

create table public.lecture_segments (
  id uuid primary key default gen_random_uuid(),
  lecture_id uuid not null references public.lectures(id) on delete cascade,
  segment_order int not null,
  segment_type text not null check (segment_type in ('video','checkpoint','exercise','exit_check')),
  title text not null,
  media_provider text,
  media_asset_key text,
  media_url text,
  duration_seconds int,
  checkpoint_id uuid references public.lecture_checkpoints(id),
  exercise_id uuid references public.lecture_exercises(id),
  is_required boolean not null default true,
  settings jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (lecture_id, segment_order),
  check (segment_type <> 'video' or media_url is not null or media_asset_key is not null),
  check (segment_type not in ('checkpoint','exit_check') or checkpoint_id is not null),
  check (segment_type <> 'exercise' or exercise_id is not null)
);

create table public.lecture_sessions (
  id uuid primary key default gen_random_uuid(),
  learner_id uuid not null references public.profiles(id) on delete cascade,
  lecture_id uuid not null references public.lectures(id) on delete cascade,
  current_segment_id uuid references public.lecture_segments(id),
  playback_position_seconds int not null default 0,
  status text not null default 'not_started' check (status in ('not_started','in_progress','completed')),
  state_version int not null default 1,
  last_seen_at timestamptz not null default now(),
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (learner_id, lecture_id)
);
create index lecture_sessions_learner_status_idx on public.lecture_sessions(learner_id, status);

create table public.checkpoint_attempts (
  id uuid primary key default gen_random_uuid(),
  learner_id uuid not null references public.profiles(id) on delete cascade,
  checkpoint_id uuid not null references public.lecture_checkpoints(id),
  question_id uuid not null references public.mcq_questions(id),
  selected_option_id text not null,
  is_correct boolean not null,
  score numeric not null,
  idempotency_key uuid not null,
  submitted_at timestamptz not null default now(),
  unique (learner_id, idempotency_key)
);
create index checkpoint_attempts_idx on public.checkpoint_attempts(learner_id, checkpoint_id, submitted_at desc);

create table public.lab_submissions (
  id uuid primary key default gen_random_uuid(),
  learner_id uuid not null references public.profiles(id) on delete cascade,
  exercise_id uuid not null references public.lecture_exercises(id),
  submission_number int not null,
  source_code text not null check (octet_length(source_code) <= 50000),
  idempotency_key uuid,
  status text not null default 'queued' check (status in ('queued','running','passed','failed','timeout','error')),
  score numeric,
  passed_tests int not null default 0,
  total_tests int not null default 0,
  safe_feedback jsonb not null default '[]',
  execution_ms int,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (learner_id, exercise_id, submission_number),
  unique (learner_id, idempotency_key)
);
create index lab_submissions_status_idx on public.lab_submissions(status, created_at);
create index lab_submissions_learner_idx on public.lab_submissions(learner_id, exercise_id, created_at desc);

create table public.student_progress (
  id uuid primary key default gen_random_uuid(),
  learner_id uuid not null references public.profiles(id) on delete cascade,
  course_id uuid not null references public.courses(id) on delete cascade,
  completed_lectures int not null default 0,
  total_lectures int not null default 0,
  progress_percent numeric not null default 0,
  updated_at timestamptz not null default now(),
  unique (learner_id, course_id)
);

create table public.audit_logs (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid,
  event_type text not null,
  resource_type text not null,
  resource_id uuid,
  request_id text,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);
create index audit_logs_event_idx on public.audit_logs(event_type, created_at);
create index audit_logs_actor_idx on public.audit_logs(actor_id, created_at);

-- updated_at triggers
do $$ declare t text; begin
  foreach t in array array['profiles','courses','modules','lectures','mcq_questions','lecture_exercises','lecture_segments','lecture_sessions','lab_submissions','student_progress'] loop
    execute format('create trigger %I before update on public.%I for each row execute function public.set_updated_at()', t||'_updated_at', t);
  end loop; end $$;

-- new auth user -> learner profile (role is never taken from client metadata)
create or replace function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  insert into public.profiles (id, display_name) values (new.id, coalesce(new.raw_user_meta_data->>'display_name',''));
  return new;
end $$;
create trigger on_auth_user_created after insert on auth.users for each row execute function public.handle_new_user();

-- RLS
alter table public.profiles enable row level security;
alter table public.courses enable row level security;
alter table public.modules enable row level security;
alter table public.lectures enable row level security;
alter table public.lecture_segments enable row level security;
alter table public.lecture_checkpoints enable row level security;
alter table public.lecture_exercises enable row level security;
alter table public.mcq_questions enable row level security;      -- no client policies: API only
alter table public.exercise_tests enable row level security;     -- no client policies: API only
alter table public.lecture_sessions enable row level security;
alter table public.checkpoint_attempts enable row level security;
alter table public.lab_submissions enable row level security;
alter table public.student_progress enable row level security;
alter table public.audit_logs enable row level security;         -- no client policies

create policy profiles_select_own on public.profiles for select to authenticated using (id = (select auth.uid()));
create policy courses_select_published on public.courses for select to authenticated using (status = 'published');
create policy modules_select_published on public.modules for select to authenticated using (status = 'published');
create policy lectures_select_published on public.lectures for select to authenticated using (status = 'published');
create policy segments_select_published on public.lecture_segments for select to authenticated
  using (exists (select 1 from public.lectures l where l.id = lecture_id and l.status = 'published'));
create policy checkpoints_select_published on public.lecture_checkpoints for select to authenticated
  using (exists (select 1 from public.lectures l where l.id = lecture_id and l.status = 'published'));
create policy exercises_select_published on public.lecture_exercises for select to authenticated using (status = 'published');
create policy sessions_select_own on public.lecture_sessions for select to authenticated using (learner_id = (select auth.uid()));
create policy attempts_select_own on public.checkpoint_attempts for select to authenticated using (learner_id = (select auth.uid()));
create policy submissions_select_own on public.lab_submissions for select to authenticated using (learner_id = (select auth.uid()));
create policy progress_select_own on public.student_progress for select to authenticated using (learner_id = (select auth.uid()));
-- No insert/update/delete policies: all writes go through the FastAPI service-role path.
