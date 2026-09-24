create function public.create_draft_job(p_admin_id uuid,p_title text,p_department text,p_location text,p_job_type public.job_type,p_description text,p_requirements text,p_deadline timestamptz,p_openings integer) returns uuid language plpgsql security definer set search_path='' as $$
declare v_id uuid:=gen_random_uuid();
begin
 perform 1 from public.profiles where id=p_admin_id and role='admin' and is_active; if not found then raise exception 'Active admin profile not found' using errcode='insufficient_privilege'; end if;
 if p_openings<=0 then raise exception 'Openings must be positive' using errcode='check_violation'; end if;
 insert into public.jobs(id,title,department,location,job_type,description,requirements,application_deadline,openings,status,created_by) values(v_id,btrim(p_title),btrim(p_department),btrim(p_location),p_job_type,btrim(p_description),btrim(p_requirements),p_deadline,p_openings,'draft',p_admin_id);
 insert into public.audit_logs(actor_id,actor_role,action,entity_type,entity_id) values(p_admin_id,'admin','draft_job_created','job',v_id); return v_id;
end;$$;
create function public.update_draft_job(p_admin_id uuid,p_job_id uuid,p_title text,p_department text,p_location text,p_job_type public.job_type,p_description text,p_requirements text,p_deadline timestamptz,p_openings integer) returns void language plpgsql security definer set search_path='' as $$
begin
 perform 1 from public.profiles where id=p_admin_id and role='admin' and is_active; if not found then raise exception 'Active admin profile not found' using errcode='insufficient_privilege'; end if;
 perform 1 from public.jobs where id=p_job_id and status='draft' for update; if not found then raise exception 'Only existing draft jobs can be edited' using errcode='check_violation'; end if;
 update public.jobs set title=btrim(p_title),department=btrim(p_department),location=btrim(p_location),job_type=p_job_type,description=btrim(p_description),requirements=btrim(p_requirements),application_deadline=p_deadline,openings=p_openings where id=p_job_id;
 insert into public.audit_logs(actor_id,actor_role,action,entity_type,entity_id) values(p_admin_id,'admin','draft_job_updated','job',p_job_id);
end;$$;
revoke all on function public.create_draft_job(uuid,text,text,text,public.job_type,text,text,timestamptz,integer) from public,anon,authenticated;
revoke all on function public.update_draft_job(uuid,uuid,text,text,text,public.job_type,text,text,timestamptz,integer) from public,anon,authenticated;
grant execute on function public.create_draft_job(uuid,text,text,text,public.job_type,text,text,timestamptz,integer) to service_role;
grant execute on function public.update_draft_job(uuid,uuid,text,text,text,public.job_type,text,text,timestamptz,integer) to service_role;
