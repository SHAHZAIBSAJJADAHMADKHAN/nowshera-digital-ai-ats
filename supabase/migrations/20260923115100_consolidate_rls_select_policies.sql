-- Phase 2E follow-up: combine equivalent permissive SELECT policies to avoid per-row policy fan-out.

drop policy "jobs: candidate reads currently open jobs" on public.jobs;
drop policy "jobs: assigned recruiter reads job" on public.jobs;
drop policy "jobs: active admin reads all" on public.jobs;
create policy "jobs: authorized browser reads job"
on public.jobs for select to authenticated
using (
  private.is_admin()
  or private.is_assigned_recruiter(id)
  or (private.is_candidate() and status = 'open' and application_deadline > now())
);

drop policy "job_recruiters: recruiter reads own assignment" on public.job_recruiters;
drop policy "job_recruiters: active admin reads all" on public.job_recruiters;
create policy "job_recruiters: authorized browser reads assignment"
on public.job_recruiters for select to authenticated
using (private.is_admin() or (private.is_active_user() and recruiter_id = (select auth.uid())));
