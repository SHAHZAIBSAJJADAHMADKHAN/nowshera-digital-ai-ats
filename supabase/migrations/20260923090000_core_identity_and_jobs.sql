-- Phase 2A: Core identity, jobs, and recruiter-assignment schema.
-- Role and job value sets are enums to make invalid persisted values impossible.

create type public.app_role as enum ('candidate', 'recruiter', 'admin');
create type public.job_type as enum ('full-time', 'part-time', 'internship');
create type public.job_status as enum ('draft', 'open', 'closed');

create function public.set_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

create table public.profiles (
  id uuid primary key references auth.users(id) on delete restrict,
  full_name text not null check (char_length(btrim(full_name)) > 0),
  email text not null unique check (email = lower(btrim(email))),
  phone text,
  role public.app_role not null default 'candidate',
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table public.profiles is
  'Application profile linked one-to-one to Supabase Auth. Auth deletion is restricted to preserve future recruitment history.';

create table public.jobs (
  id uuid primary key default gen_random_uuid(),
  title text not null check (char_length(btrim(title)) > 0),
  department text not null check (char_length(btrim(department)) > 0),
  location text not null check (char_length(btrim(location)) > 0),
  job_type public.job_type not null,
  description text not null,
  requirements text not null,
  application_deadline timestamptz not null,
  openings integer not null check (openings > 0),
  status public.job_status not null default 'draft',
  created_by uuid not null references public.profiles(id) on delete restrict,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  closed_at timestamptz,
  constraint jobs_closed_at_after_created_at
    check (closed_at is null or closed_at >= created_at)
);

comment on table public.jobs is
  'Admin-managed job records. Profile deletion is restricted so future recruitment history remains attributable.';

create table public.job_recruiters (
  job_id uuid not null references public.jobs(id) on delete restrict,
  recruiter_id uuid not null references public.profiles(id) on delete restrict,
  assigned_by uuid not null references public.profiles(id) on delete restrict,
  assigned_at timestamptz not null default now(),
  primary key (job_id, recruiter_id)
);

comment on table public.job_recruiters is
  'Recruiter-to-job assignment join table. Composite primary key prevents duplicate assignments.';

create trigger set_profiles_updated_at
before update on public.profiles
for each row execute function public.set_updated_at();

create trigger set_jobs_updated_at
before update on public.jobs
for each row execute function public.set_updated_at();

create index profiles_active_role_idx
  on public.profiles (role)
  where is_active;
create index jobs_status_idx on public.jobs (status);
create index jobs_application_deadline_idx on public.jobs (application_deadline);
create index jobs_department_idx on public.jobs (department);
create index job_recruiters_recruiter_id_idx on public.job_recruiters (recruiter_id);

alter table public.profiles enable row level security;
alter table public.jobs enable row level security;
alter table public.job_recruiters enable row level security;

-- The timestamp trigger is internal and should not be callable as a public RPC.
revoke all on function public.set_updated_at() from public;
