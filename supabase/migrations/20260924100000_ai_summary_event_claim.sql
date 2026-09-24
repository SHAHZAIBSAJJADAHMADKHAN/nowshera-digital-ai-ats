-- Phase 9B-2 Step 1: dedicated, service-only AI outbox claim boundary.

create function public.claim_ai_summary_events(
  p_limit integer default 10
)
returns table(
  event_id uuid,
  application_id uuid,
  attempt_count integer,
  created_at timestamptz
)
language plpgsql
security definer
set search_path = ''
as $$
begin
  if p_limit < 1 or p_limit > 25 then
    raise exception 'Claim limit must be between 1 and 25' using errcode = 'check_violation';
  end if;

  return query
  with eligible as (
    select e.id
    from public.automation_events as e
    where e.status = 'pending'
      and e.available_at <= now()
      and e.event_type = 'ai_summary_requested'
    order by e.available_at, e.created_at, e.id
    for update skip locked
    limit p_limit
  ), claimed as (
    update public.automation_events as e
    set status = 'processing', attempt_count = e.attempt_count + 1
    from eligible
    where e.id = eligible.id
    returning e.id, e.aggregate_id, e.attempt_count, e.created_at
  )
  select c.id, c.aggregate_id, c.attempt_count, c.created_at
  from claimed as c
  order by c.created_at, c.id;
end;
$$;

revoke all on function public.claim_ai_summary_events(integer) from public, anon, authenticated;
grant execute on function public.claim_ai_summary_events(integer) to service_role;
