-- 0007: certificates, portfolio evidence, announcements, named cohorts, issue reports.
-- All access is through the API (service role). RLS is enabled with no policies, so anon/authenticated cannot read or write directly.

create table public.certificates (
  id uuid primary key default gen_random_uuid(),
  learner_id uuid not null references public.profiles(id) on delete cascade,
  course_id uuid not null references public.courses(id) on delete cascade,
  serial text not null unique,
  completed_lectures int not null,
  issued_at timestamptz not null default now(),
  revoked_at timestamptz,
  unique (learner_id, course_id)
);

create table public.portfolio_items (
  id uuid primary key default gen_random_uuid(),
  learner_id uuid not null references public.profiles(id) on delete cascade,
  submission_id uuid not null unique references public.lab_submissions(id) on delete cascade,
  exercise_id uuid not null references public.lecture_exercises(id),
  title text not null check (char_length(title) between 1 and 120),
  note text not null default '' check (char_length(note) <= 1000),
  created_at timestamptz not null default now()
);
create index portfolio_items_learner_idx on public.portfolio_items(learner_id, created_at desc);

create table public.announcements (
  id uuid primary key default gen_random_uuid(),
  author_id uuid not null references public.profiles(id) on delete cascade,
  course_id uuid not null references public.courses(id) on delete cascade,
  scope text not null check (scope in ('assigned', 'course')),
  title text not null check (char_length(title) between 1 and 120),
  body text not null check (char_length(body) between 1 and 2000),
  created_at timestamptz not null default now(),
  archived_at timestamptz
);
create index announcements_course_idx on public.announcements(course_id, created_at desc);

create table public.cohorts (
  id uuid primary key default gen_random_uuid(),
  course_id uuid not null references public.courses(id) on delete cascade,
  name text not null check (char_length(name) between 1 and 80),
  created_by uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  archived_at timestamptz,
  unique (course_id, name)
);
create table public.cohort_members (
  cohort_id uuid not null references public.cohorts(id) on delete cascade,
  learner_id uuid not null references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (cohort_id, learner_id)
);
create table public.cohort_teachers (
  cohort_id uuid not null references public.cohorts(id) on delete cascade,
  teacher_id uuid not null references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (cohort_id, teacher_id)
);

create table public.issue_reports (
  id uuid primary key default gen_random_uuid(),
  reporter_id uuid not null references public.profiles(id) on delete cascade,
  category text not null check (category in ('content', 'grading', 'account', 'accessibility', 'other')),
  message text not null check (char_length(message) between 5 and 2000),
  page text check (page is null or char_length(page) <= 300),
  status text not null default 'open' check (status in ('open', 'triaged', 'resolved', 'dismissed')),
  admin_note text check (admin_note is null or char_length(admin_note) <= 1000),
  resolved_by uuid references public.profiles(id) on delete set null,
  correlation_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index issue_reports_status_idx on public.issue_reports(status, created_at desc);

create trigger issue_reports_updated before update on public.issue_reports
  for each row execute function public.set_updated_at();

alter table public.certificates enable row level security;
alter table public.portfolio_items enable row level security;
alter table public.announcements enable row level security;
alter table public.cohorts enable row level security;
alter table public.cohort_members enable row level security;
alter table public.cohort_teachers enable row level security;
alter table public.issue_reports enable row level security;

revoke all on public.certificates, public.portfolio_items, public.announcements, public.cohorts, public.cohort_members,
  public.cohort_teachers, public.issue_reports from anon, authenticated;
