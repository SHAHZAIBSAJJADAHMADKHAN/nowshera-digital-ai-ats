from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "supabase" / "migrations"


def migration(name: str) -> str:
    return (MIGRATIONS / name).read_text(encoding="utf-8").lower()


def compact(text: str) -> str:
    return " ".join(text.split())


def test_recruiter_state_machine_sql_blocks_skips_backwards_terminals_and_closed_job_escalation():
    text = compact(migration("20260923103000_recruiter_stage_state_machine.sql"))
    for fragment in (
        "if v_stage in ('hired', 'rejected', 'withdrawn') then",
        "if v_job_status = 'closed' and p_target_stage <> 'rejected' then",
        "if p_target_stage = 'rejected' then",
        "if v_stage not in ('applied', 'shortlisted', 'interview', 'offer') then",
        "elsif (v_stage = 'applied' and p_target_stage = 'shortlisted') or (v_stage = 'interview' and p_target_stage = 'offer') then",
        "else raise exception 'transition from % to % is not permitted by this operation'",
    ):
        assert fragment in text
    assert "v_stage = 'shortlisted' and p_target_stage = 'interview'" not in text
    assert "p_target_stage = 'hired'" not in text


def test_recruiter_stage_rpc_requires_an_active_assignment_server_side():
    text = compact(migration("20260923103000_recruiter_stage_state_machine.sql"))
    for fragment in (
        "where id = p_recruiter_id and role = 'recruiter' and is_active",
        "from public.job_recruiters where job_id = v_job_id and recruiter_id = p_recruiter_id",
        "raise exception 'recruiter is not assigned to this job' using errcode = 'insufficient_privilege'",
        "revoke all on function public.transition_recruiter_application(uuid, uuid, public.application_stage) from public, anon, authenticated",
        "grant execute on function public.transition_recruiter_application(uuid, uuid, public.application_stage) to service_role",
    ):
        assert fragment in text


def test_interview_sql_requires_future_one_hour_no_same_recruiter_overlap_and_allows_boundaries():
    table = migration("20260923095000_interviews_ai_outbox_audit.sql")
    rpc = migration("20260923105000_atomic_interview_scheduling.sql")
    for fragment in (
        "application_id uuid not null unique",
        "constraint interviews_exactly_one_hour check (ends_at = starts_at + interval '1 hour')",
        "constraint interviews_recruiter_no_overlap exclude using gist",
        "tstzrange(starts_at, ends_at, '[)') with &&",
    ):
        assert fragment in table
    for fragment in (
        "if p_starts_at <= now() then",
        "p_starts_at+interval '1 hour'",
        "values(v_interview_id,p_application_id,p_recruiter_id,p_starts_at,p_starts_at+interval '1 hour'",
    ):
        assert fragment in rpc


def test_hiring_capacity_auto_close_and_submission_invariants_are_sql_enforced():
    submit = migration("20260923101000_application_submission_and_withdrawal.sql")
    base = migration("20260923093000_cv_applications_and_notes.sql")
    hire = migration("20260923111000_hiring_capacity_and_auto_close.sql")
    for fragment in (
        "create unique index applications_one_active_per_candidate_job_idx",
        "where stage in ('applied', 'shortlisted', 'interview', 'offer')",
        "if v_deadline <= now() then",
        "if v_openings <= 0 then",
        "p_candidate_id, p_job_id, p_cv_id",
        "'application-received:' || v_application_id::text",
    ):
        assert fragment in (base + submit)
    for fragment in (
        "if v_stage <> 'offer' then",
        "if v_status <> 'open' then",
        "if v_hired >= v_openings then raise exception 'job capacity is filled'",
        "update public.applications set stage='hired'",
        "update public.jobs set status='closed',closed_at=now()",
        "'application-hired:'||p_application_id::text",
    ):
        assert fragment in hire


def test_automation_outbox_sql_has_claim_retry_terminal_failure_and_idempotency_guards():
    table = compact(migration("20260923095000_interviews_ai_outbox_audit.sql"))
    delivery = compact(migration("20260923200000_automation_outbox_delivery.sql"))
    projection = compact(migration("20260923210000_email_delivery_claim_projection.sql"))
    fixed = compact(migration("20260923200100_fix_automation_outbox_return_columns.sql"))
    for fragment in (
        "idempotency_key text not null unique",
        "status public.processing_status not null default 'pending'",
        "attempt_count integer not null default 0",
    ):
        assert fragment in table
    for fragment in (
        "for update skip locked",
        "status = 'processing'",
        "attempt_count = e.attempt_count + 1",
        "where e.status = 'pending'",
        "event_type = any(p_event_types)",
        "status = 'completed'",
    ):
        assert fragment in delivery + projection
    for fragment in (
        "case when public.automation_events.attempt_count >= 3 then 'failed'::public.processing_status else 'pending'::public.processing_status end",
        "case when public.automation_events.attempt_count >= 3 then public.automation_events.available_at else now() + interval '5 minutes' end",
    ):
        assert fragment in fixed


def test_ai_retry_sql_does_not_replay_application_received_email_event():
    text = migration("20260924090000_ai_summary_result_and_retry.sql")
    assert "retry_ai_summary" in text
    assert "actor cannot retry this ai summary" in text
    assert "v_status not in ('failed')" in text
    assert "'ai_summary_requested'" in text
    assert "'ai-summary-retry:'||p_application_id::text||':'||(v_attempt+1)::text" in text
    assert "application_received" not in text
