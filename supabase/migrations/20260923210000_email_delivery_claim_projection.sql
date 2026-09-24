-- Phase 8B: service-only email delivery projection. Outbox rows remain ID-first.

create function public.claim_email_delivery_events(
  p_event_types text[],
  p_limit integer default 10
)
returns table(
  event_id uuid,
  event_type text,
  aggregate_type text,
  aggregate_id uuid,
  payload jsonb,
  attempt_count integer,
  created_at timestamptz,
  recipient_email text,
  candidate_name text,
  job_title text,
  interview_starts_at timestamptz,
  interview_location text,
  interview_meeting_link text
)
language plpgsql security definer set search_path = '' as $$
begin
  if coalesce(cardinality(p_event_types), 0) = 0
     or cardinality(p_event_types) > 4
     or exists (
       select 1 from unnest(p_event_types) as requested(event_type)
       where requested.event_type not in (
         'application_received', 'interview_invitation',
         'application_hired', 'application_rejected'
       )
     ) then
    raise exception 'Only supported email event types can be claimed' using errcode = 'check_violation';
  end if;
  if p_limit < 1 or p_limit > 25 then
    raise exception 'Claim limit must be between 1 and 25' using errcode = 'check_violation';
  end if;

  return query
  with eligible as (
    select e.id
    from public.automation_events as e
    where e.status = 'pending'
      and e.available_at <= now()
      and e.event_type = any(p_event_types)
    order by e.available_at, e.created_at, e.id
    for update skip locked
    limit p_limit
  ), claimed as (
    update public.automation_events as e
    set status = 'processing', attempt_count = e.attempt_count + 1
    from eligible
    where e.id = eligible.id
    returning e.id, e.event_type, e.aggregate_type, e.aggregate_id,
      e.payload, e.attempt_count, e.created_at
  )
  select c.id, c.event_type, c.aggregate_type, c.aggregate_id, c.payload,
    c.attempt_count, c.created_at, candidate.email, candidate.full_name,
    j.title, i.starts_at, i.location, i.meeting_link
  from claimed as c
  join public.applications as a on a.id = case
    when c.event_type = 'interview_invitation' then (c.payload ->> 'application_id')::uuid
    else c.aggregate_id
  end
  join public.profiles as candidate on candidate.id = a.candidate_id
  join public.jobs as j on j.id = a.job_id
  left join public.interviews as i on i.id = c.aggregate_id
    and c.event_type = 'interview_invitation'
  order by c.created_at, c.id;
end;
$$;

revoke all on function public.claim_email_delivery_events(text[], integer) from public, anon, authenticated;
grant execute on function public.claim_email_delivery_events(text[], integer) to service_role;
