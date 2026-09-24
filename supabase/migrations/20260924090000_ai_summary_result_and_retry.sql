-- Phase 9A: trusted AI-result ingestion and authorized retry; no provider call occurs here.

create function public.retry_ai_summary(p_actor_id uuid, p_application_id uuid)
returns void language plpgsql security definer set search_path = '' as $$
declare v_job_id uuid; v_attempt integer; v_status public.processing_status;
begin
  select a.job_id into v_job_id from public.applications a where a.id=p_application_id for update;
  if not found then raise exception 'Application not found' using errcode='foreign_key_violation'; end if;
  if not exists (select 1 from public.profiles p where p.id=p_actor_id and p.is_active and (p.role='admin' or (p.role='recruiter' and exists (select 1 from public.job_recruiters jr where jr.job_id=v_job_id and jr.recruiter_id=p_actor_id)))) then
    raise exception 'Actor cannot retry this AI summary' using errcode='insufficient_privilege';
  end if;
  select status,attempt_count into v_status,v_attempt from public.ai_summaries where application_id=p_application_id for update;
  if found and v_status not in ('failed') then raise exception 'AI summary is not available for retry' using errcode='check_violation'; end if;
  if not found then
    v_attempt:=0;
    insert into public.ai_summaries(application_id,status) values(p_application_id,'pending');
  else
    update public.ai_summaries set status='pending',profile_summary=null,requirements_found=null,requirements_not_found=null,interview_questions=null,error_message=null,generated_at=null where application_id=p_application_id;
  end if;
  insert into public.automation_events(event_type,aggregate_type,aggregate_id,payload,idempotency_key)
  values('ai_summary_requested','application',p_application_id,jsonb_build_object('application_id',p_application_id),'ai-summary-retry:'||p_application_id::text||':'||(v_attempt+1)::text)
  on conflict(idempotency_key) do nothing;
end;
$$;

create function public.save_ai_summary_result(p_application_id uuid,p_status public.processing_status,p_profile_summary jsonb default null,p_requirements_found jsonb default null,p_requirements_not_found jsonb default null,p_interview_questions jsonb default null,p_error_message text default null)
returns void language plpgsql security definer set search_path = '' as $$
begin
  if p_status not in ('completed','failed') then raise exception 'Only completed or failed AI results are accepted' using errcode='check_violation'; end if;
  if not exists(select 1 from public.applications where id=p_application_id) then raise exception 'Application not found' using errcode='foreign_key_violation'; end if;
  if p_status='completed' and not (jsonb_typeof(p_profile_summary)='array' and jsonb_array_length(p_profile_summary) between 3 and 5 and jsonb_typeof(p_requirements_found)='array' and jsonb_typeof(p_requirements_not_found)='array' and jsonb_typeof(p_interview_questions)='array' and jsonb_array_length(p_interview_questions)=3 and p_error_message is null) then raise exception 'Completed AI result has invalid structure' using errcode='check_violation'; end if;
  if p_status='failed' and (nullif(btrim(p_error_message),'') is null or p_profile_summary is not null or p_requirements_found is not null or p_requirements_not_found is not null or p_interview_questions is not null) then raise exception 'Failed AI result requires only a safe error message' using errcode='check_violation'; end if;
  insert into public.ai_summaries(application_id,status,profile_summary,requirements_found,requirements_not_found,interview_questions,error_message,attempt_count,generated_at)
  values(p_application_id,p_status,p_profile_summary,p_requirements_found,p_requirements_not_found,p_interview_questions,case when p_status='failed' then left(btrim(p_error_message),500) else null end,1,case when p_status='completed' then now() else null end)
  on conflict(application_id) do update set status=excluded.status,profile_summary=excluded.profile_summary,requirements_found=excluded.requirements_found,requirements_not_found=excluded.requirements_not_found,interview_questions=excluded.interview_questions,error_message=excluded.error_message,attempt_count=public.ai_summaries.attempt_count+1,generated_at=excluded.generated_at;
end;
$$;

revoke all on function public.retry_ai_summary(uuid,uuid) from public,anon,authenticated;
revoke all on function public.save_ai_summary_result(uuid,public.processing_status,jsonb,jsonb,jsonb,jsonb,text) from public,anon,authenticated;
grant execute on function public.retry_ai_summary(uuid,uuid) to service_role;
grant execute on function public.save_ai_summary_result(uuid,public.processing_status,jsonb,jsonb,jsonb,jsonb,text) to service_role;
