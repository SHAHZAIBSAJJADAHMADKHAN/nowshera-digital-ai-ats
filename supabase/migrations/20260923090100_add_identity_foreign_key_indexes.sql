-- Phase 2A follow-up: cover foreign keys identified by the database advisor.

create index jobs_created_by_idx on public.jobs (created_by);
create index job_recruiters_assigned_by_idx on public.job_recruiters (assigned_by);
