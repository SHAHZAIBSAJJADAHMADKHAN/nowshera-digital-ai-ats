-- Phase 2D-3: the only approved path for shortlisted -> interview.
create function public.schedule_interview(p_recruiter_id uuid, p_application_id uuid, p_starts_at timestamptz, p_location text default null, p_meeting_link text default null)
returns uuid language plpgsql security definer set search_path = '' as $$
declare v_stage public.application_stage; v_job_id uuid; v_job_status public.job_status; v_interview_id uuid := gen_random_uuid(); v_location text := nullif(btrim(p_location), ''); v_link text := nullif(btrim(p_meeting_link), '');
begin
  perform 1 from public.profiles where id=p_recruiter_id and role='recruiter' and is_active;
  if not found then raise exception 'Active recruiter profile not found' using errcode='foreign_key_violation'; end if;
  select a.stage,a.job_id,j.status into v_stage,v_job_id,v_job_status from public.applications a join public.jobs j on j.id=a.job_id where a.id=p_application_id for update of a;
  if not found then raise exception 'Application not found' using errcode='foreign_key_violation'; end if;
  perform 1 from public.job_recruiters where job_id=v_job_id and recruiter_id=p_recruiter_id;
  if not found then raise exception 'Recruiter is not assigned to this job' using errcode='insufficient_privilege'; end if;
  if v_stage <> 'shortlisted' then raise exception 'Application must be shortlisted' using errcode='check_violation'; end if;
  if v_job_status <> 'open' then raise exception 'Job must be open' using errcode='check_violation'; end if;
  if p_starts_at <= now() then raise exception 'Interview must start in the future' using errcode='check_violation'; end if;
  if v_location is null and v_link is null then raise exception 'Location or meeting link is required' using errcode='check_violation'; end if;
  insert into public.interviews(id,application_id,recruiter_id,starts_at,ends_at,location,meeting_link) values(v_interview_id,p_application_id,p_recruiter_id,p_starts_at,p_starts_at+interval '1 hour',v_location,v_link);
  update public.applications set stage='interview' where id=p_application_id;
  insert into public.application_stage_history(application_id,from_stage,to_stage,changed_by) values(p_application_id,'shortlisted','interview',p_recruiter_id);
  insert into public.automation_events(event_type,aggregate_type,aggregate_id,payload,idempotency_key) values('interview_invitation','interview',v_interview_id,jsonb_build_object('application_id',p_application_id,'interview_id',v_interview_id,'starts_at',p_starts_at),'interview-invitation:'||v_interview_id::text);
  insert into public.audit_logs(actor_id,actor_role,action,entity_type,entity_id,metadata) values(p_recruiter_id,'recruiter','interview_scheduled','interview',v_interview_id,jsonb_build_object('application_id',p_application_id,'job_id',v_job_id,'starts_at',p_starts_at,'ends_at',p_starts_at+interval '1 hour','has_location',v_location is not null,'has_meeting_link',v_link is not null));
  return v_interview_id;
end; $$;
revoke all on function public.schedule_interview(uuid,uuid,timestamptz,text,text) from public,anon,authenticated;
grant execute on function public.schedule_interview(uuid,uuid,timestamptz,text,text) to service_role;
