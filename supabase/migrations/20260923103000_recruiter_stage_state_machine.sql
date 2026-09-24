-- Phase 2D-2: restricted recruiter stage transitions and rejection.

create function public.transition_recruiter_application(
  p_recruiter_id uuid,
  p_application_id uuid,
  p_target_stage public.application_stage
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_stage public.application_stage;
  v_job_id uuid;
  v_job_status public.job_status;
begin
  perform 1 from public.profiles
  where id = p_recruiter_id and role = 'recruiter' and is_active;
  if not found then
    raise exception 'Active recruiter profile not found' using errcode = 'foreign_key_violation';
  end if;

  select a.stage, a.job_id, j.status into v_stage, v_job_id, v_job_status
  from public.applications a join public.jobs j on j.id = a.job_id
  where a.id = p_application_id
  for update of a;
  if not found then
    raise exception 'Application not found' using errcode = 'foreign_key_violation';
  end if;

  perform 1 from public.job_recruiters
  where job_id = v_job_id and recruiter_id = p_recruiter_id;
  if not found then
    raise exception 'Recruiter is not assigned to this job' using errcode = 'insufficient_privilege';
  end if;

  if v_stage in ('hired', 'rejected', 'withdrawn') then
    raise exception 'Terminal applications cannot transition' using errcode = 'check_violation';
  end if;
  if v_job_status = 'closed' and p_target_stage <> 'rejected' then
    raise exception 'Closed jobs only permit rejection of active applications' using errcode = 'check_violation';
  end if;

  if p_target_stage = 'rejected' then
    if v_stage not in ('applied', 'shortlisted', 'interview', 'offer') then
      raise exception 'Application cannot be rejected from stage %', v_stage using errcode = 'check_violation';
    end if;
  elsif (v_stage = 'applied' and p_target_stage = 'shortlisted')
     or (v_stage = 'interview' and p_target_stage = 'offer') then
    null;
  else
    raise exception 'Transition from % to % is not permitted by this operation', v_stage, p_target_stage using errcode = 'check_violation';
  end if;

  update public.applications set stage = p_target_stage where id = p_application_id;
  insert into public.application_stage_history(application_id, from_stage, to_stage, changed_by)
  values (p_application_id, v_stage, p_target_stage, p_recruiter_id);
  if p_target_stage = 'rejected' then
    insert into public.automation_events(event_type, aggregate_type, aggregate_id, payload, idempotency_key)
    values ('application_rejected', 'application', p_application_id,
      jsonb_build_object('application_id', p_application_id), 'application-rejected:' || p_application_id::text)
    on conflict (idempotency_key) do nothing;
  end if;
  insert into public.audit_logs(actor_id, actor_role, action, entity_type, entity_id, old_values, new_values, metadata)
  values (p_recruiter_id, 'recruiter', 'application_stage_changed', 'application', p_application_id,
    jsonb_build_object('stage', v_stage), jsonb_build_object('stage', p_target_stage), jsonb_build_object('job_id', v_job_id));
end;
$$;

revoke all on function public.transition_recruiter_application(uuid, uuid, public.application_stage) from public, anon, authenticated;
grant execute on function public.transition_recruiter_application(uuid, uuid, public.application_stage) to service_role;
