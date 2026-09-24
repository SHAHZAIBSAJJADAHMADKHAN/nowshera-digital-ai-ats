-- Phase 2E: browser-facing least-privilege reads. Trusted business writes stay service-role-only.

create schema if not exists private;
revoke all on schema private from public, anon;
grant usage on schema private to authenticated;

create function private.is_active_user()
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from public.profiles p
    where p.id = (select auth.uid()) and p.is_active
  );
$$;

create function private.is_candidate()
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from public.profiles p
    where p.id = (select auth.uid()) and p.role = 'candidate' and p.is_active
  );
$$;

create function private.is_admin()
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from public.profiles p
    where p.id = (select auth.uid()) and p.role = 'admin' and p.is_active
  );
$$;

create function private.is_assigned_recruiter(p_job_id uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (
    select 1
    from public.profiles p
    join public.job_recruiters jr on jr.recruiter_id = p.id
    where p.id = (select auth.uid())
      and p.role = 'recruiter'
      and p.is_active
      and jr.job_id = p_job_id
  );
$$;

create function private.is_assigned_recruiter_for_application(p_application_id uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (
    select 1
    from public.applications a
    join public.job_recruiters jr on jr.job_id = a.job_id
    join public.profiles p on p.id = jr.recruiter_id
    where a.id = p_application_id
      and p.id = (select auth.uid())
      and p.role = 'recruiter'
      and p.is_active
  );
$$;

create function private.can_access_application(p_application_id uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select private.is_admin()
    or exists (
      select 1 from public.applications a
      where a.id = p_application_id
        and a.candidate_id = (select auth.uid())
        and private.is_candidate()
    )
    or private.is_assigned_recruiter_for_application(p_application_id);
$$;

create function private.can_access_cv_snapshot(p_cv_id uuid, p_candidate_id uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select private.is_admin()
    or exists (
      select 1 from public.candidate_cvs cv
      where cv.id = p_cv_id
        and cv.candidate_id = p_candidate_id
        and cv.candidate_id = (select auth.uid())
        and private.is_candidate()
    )
    or exists (
      select 1
      from public.applications a
      join public.job_recruiters jr on jr.job_id = a.job_id
      join public.profiles p on p.id = jr.recruiter_id
      where a.cv_id = p_cv_id
        and a.candidate_id = p_candidate_id
        and p.id = (select auth.uid())
        and p.role = 'recruiter'
        and p.is_active
    );
$$;

revoke all on function private.is_active_user() from public, anon, authenticated;
revoke all on function private.is_candidate() from public, anon, authenticated;
revoke all on function private.is_admin() from public, anon, authenticated;
revoke all on function private.is_assigned_recruiter(uuid) from public, anon, authenticated;
revoke all on function private.is_assigned_recruiter_for_application(uuid) from public, anon, authenticated;
revoke all on function private.can_access_application(uuid) from public, anon, authenticated;
revoke all on function private.can_access_cv_snapshot(uuid, uuid) from public, anon, authenticated;
grant execute on function private.is_active_user() to authenticated;
grant execute on function private.is_candidate() to authenticated;
grant execute on function private.is_admin() to authenticated;
grant execute on function private.is_assigned_recruiter(uuid) to authenticated;
grant execute on function private.is_assigned_recruiter_for_application(uuid) to authenticated;
grant execute on function private.can_access_application(uuid) to authenticated;
grant execute on function private.can_access_cv_snapshot(uuid, uuid) to authenticated;

revoke all on all tables in schema public from anon, authenticated;
grant select on public.profiles, public.jobs, public.job_recruiters, public.candidate_cvs,
  public.applications, public.application_stage_history, public.recruiter_notes,
  public.interviews, public.ai_summaries to authenticated;

create policy "profiles: active user reads self or active admin reads all"
on public.profiles for select to authenticated
using (private.is_active_user() and (id = (select auth.uid()) or private.is_admin()));

create policy "jobs: candidate reads currently open jobs"
on public.jobs for select to authenticated
using (private.is_candidate() and status = 'open' and application_deadline > now());
create policy "jobs: assigned recruiter reads job"
on public.jobs for select to authenticated
using (private.is_assigned_recruiter(id));
create policy "jobs: active admin reads all"
on public.jobs for select to authenticated
using (private.is_admin());

create policy "job_recruiters: recruiter reads own assignment"
on public.job_recruiters for select to authenticated
using (private.is_active_user() and recruiter_id = (select auth.uid()));
create policy "job_recruiters: active admin reads all"
on public.job_recruiters for select to authenticated
using (private.is_admin());

create policy "candidate_cvs: exact authorized snapshots only"
on public.candidate_cvs for select to authenticated
using (private.can_access_cv_snapshot(id, candidate_id));

create policy "applications: authorized participant reads application"
on public.applications for select to authenticated
using (private.can_access_application(id));

create policy "application_stage_history: authorized participant reads history"
on public.application_stage_history for select to authenticated
using (private.can_access_application(application_id));

create policy "recruiter_notes: assigned recruiting team reads notes"
on public.recruiter_notes for select to authenticated
using (private.is_assigned_recruiter_for_application(application_id));

create policy "interviews: authorized participant reads interview"
on public.interviews for select to authenticated
using (private.can_access_application(application_id));

create policy "ai_summaries: admin or assigned recruiter reads summary"
on public.ai_summaries for select to authenticated
using (private.is_admin() or private.is_assigned_recruiter_for_application(application_id));
