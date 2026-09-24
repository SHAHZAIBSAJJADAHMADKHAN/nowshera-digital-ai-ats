-- Phase 2D-4: capacity-safe offer -> hired transaction.
create function public.hire_application(p_recruiter_id uuid, p_application_id uuid)
returns void language plpgsql security definer set search_path = '' as $$
declare v_job_id uuid; v_stage public.application_stage; v_status public.job_status; v_openings integer; v_hired integer;
begin
  perform 1 from public.profiles where id=p_recruiter_id and role='recruiter' and is_active;
  if not found then raise exception 'Active recruiter profile not found' using errcode='foreign_key_violation'; end if;
  select job_id into v_job_id from public.applications where id=p_application_id;
  if not found then raise exception 'Application not found' using errcode='foreign_key_violation'; end if;
  select status,openings into v_status,v_openings from public.jobs where id=v_job_id for update;
  if v_status <> 'open' then raise exception 'Job must be open to hire' using errcode='check_violation'; end if;
  select stage into v_stage from public.applications where id=p_application_id for update;
  if v_stage <> 'offer' then raise exception 'Application must be at offer stage' using errcode='check_violation'; end if;
  perform 1 from public.job_recruiters where job_id=v_job_id and recruiter_id=p_recruiter_id;
  if not found then raise exception 'Recruiter is not assigned to this job' using errcode='insufficient_privilege'; end if;
  select count(*) into v_hired from public.applications where job_id=v_job_id and stage='hired';
  if v_hired >= v_openings then raise exception 'Job capacity is filled' using errcode='check_violation'; end if;
  update public.applications set stage='hired' where id=p_application_id;
  insert into public.application_stage_history(application_id,from_stage,to_stage,changed_by) values(p_application_id,'offer','hired',p_recruiter_id);
  insert into public.automation_events(event_type,aggregate_type,aggregate_id,payload,idempotency_key) values('application_hired','application',p_application_id,jsonb_build_object('application_id',p_application_id),'application-hired:'||p_application_id::text) on conflict(idempotency_key) do nothing;
  insert into public.audit_logs(actor_id,actor_role,action,entity_type,entity_id,old_values,new_values,metadata) values(p_recruiter_id,'recruiter','application_hired','application',p_application_id,jsonb_build_object('stage','offer'),jsonb_build_object('stage','hired'),jsonb_build_object('job_id',v_job_id,'hired_count_before',v_hired));
  v_hired:=v_hired+1;
  if v_hired >= v_openings then
    update public.jobs set status='closed',closed_at=now() where id=v_job_id;
    insert into public.audit_logs(actor_id,actor_role,action,entity_type,entity_id,metadata) values(p_recruiter_id,'recruiter','job_auto_closed','job',v_job_id,jsonb_build_object('reason','opening_capacity_filled','hired_count',v_hired));
  end if;
end; $$;
revoke all on function public.hire_application(uuid,uuid) from public,anon,authenticated;
grant execute on function public.hire_application(uuid,uuid) to service_role;
