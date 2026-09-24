-- Phase 2D-1: atomic application submission and candidate withdrawal.

create function public.submit_application(
  p_candidate_id uuid,
  p_job_id uuid,
  p_cv_id uuid
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_application_id uuid := gen_random_uuid();
  v_deadline timestamptz;
  v_openings integer;
begin
  perform 1 from public.profiles
  where id = p_candidate_id and role = 'candidate' and is_active
  for update;
  if not found then
    raise exception 'Active candidate profile not found' using errcode = 'foreign_key_violation';
  end if;

  select application_deadline, openings into v_deadline, v_openings
  from public.jobs
  where id = p_job_id and status = 'open'
  for update;
  if not found then
    raise exception 'Open job not found' using errcode = 'check_violation';
  end if;
  if v_deadline <= now() then
    raise exception 'Application deadline has passed' using errcode = 'check_violation';
  end if;
  if v_openings <= 0 then
    raise exception 'Job has no available capacity' using errcode = 'check_violation';
  end if;

  perform 1 from public.candidate_cvs
  where id = p_cv_id and candidate_id = p_candidate_id;
  if not found then
    raise exception 'Candidate CV not found' using errcode = 'foreign_key_violation';
  end if;

  insert into public.applications (id, candidate_id, job_id, cv_id, stage)
  values (v_application_id, p_candidate_id, p_job_id, p_cv_id, 'applied');
  insert into public.application_stage_history (application_id, from_stage, to_stage, changed_by)
  values (v_application_id, null, 'applied', p_candidate_id);
  insert into public.ai_summaries (application_id, status)
  values (v_application_id, 'pending');
  insert into public.automation_events (event_type, aggregate_type, aggregate_id, payload, idempotency_key)
  values
    ('application_received', 'application', v_application_id, jsonb_build_object('application_id', v_application_id), 'application-received:' || v_application_id::text),
    ('ai_summary_requested', 'application', v_application_id, jsonb_build_object('application_id', v_application_id), 'ai-summary:' || v_application_id::text);
  insert into public.audit_logs (actor_id, actor_role, action, entity_type, entity_id, new_values, metadata)
  values (p_candidate_id, 'candidate', 'application_submitted', 'application', v_application_id,
    jsonb_build_object('job_id', p_job_id, 'cv_id', p_cv_id, 'stage', 'applied'), '{}'::jsonb);
  return v_application_id;
end;
$$;

create function public.withdraw_application(
  p_candidate_id uuid,
  p_application_id uuid
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_stage public.application_stage;
begin
  select stage into v_stage from public.applications
  where id = p_application_id and candidate_id = p_candidate_id
  for update;
  if not found then
    raise exception 'Candidate application not found' using errcode = 'foreign_key_violation';
  end if;
  if v_stage not in ('applied', 'shortlisted', 'interview', 'offer') then
    raise exception 'Application cannot be withdrawn from stage %', v_stage using errcode = 'check_violation';
  end if;
  update public.applications
  set stage = 'withdrawn', withdrawn_at = now()
  where id = p_application_id;
  insert into public.application_stage_history (application_id, from_stage, to_stage, changed_by)
  values (p_application_id, v_stage, 'withdrawn', p_candidate_id);
  insert into public.audit_logs (actor_id, actor_role, action, entity_type, entity_id, old_values, new_values)
  values (p_candidate_id, 'candidate', 'application_withdrawn', 'application', p_application_id,
    jsonb_build_object('stage', v_stage), jsonb_build_object('stage', 'withdrawn'));
end;
$$;

revoke all on function public.submit_application(uuid, uuid, uuid) from public, anon, authenticated;
revoke all on function public.withdraw_application(uuid, uuid) from public, anon, authenticated;
grant execute on function public.submit_application(uuid, uuid, uuid) to service_role;
grant execute on function public.withdraw_application(uuid, uuid) to service_role;
