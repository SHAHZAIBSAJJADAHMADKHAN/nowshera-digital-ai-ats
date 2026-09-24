# Phase 2D-5 — Job Lifecycle Completion

Jobs retain the three-state lifecycle `draft → open → closed`. `open_job` is the only trusted draft-to-open operation: it requires an active admin, locks the job row, verifies all publication text fields are non-blank, verifies positive openings, and requires `application_deadline > now()`. It clears `closed_at` and records `job_opened`. Open and closed jobs cannot be reopened.

`close_job` permits an active admin to close either a draft or open job. It locks the job row, writes `closed` and database time to `closed_at`, and records `job_manually_closed`. A repeat close returns `false`, retaining the original timestamp and producing no duplicate audit record.

`close_expired_jobs` is the service-role-only foundation for a future scheduler. It locks every qualifying open job and closes those with `application_deadline <= now()`; each changed row gets a `job_deadline_closed` audit record with no actor. It returns the number closed. A subsequent call finds no qualifying closed rows, so it returns zero and writes no duplicate audit records. All comparisons are `timestamptz` and the deadline boundary is inclusive: a deadline at or before database time is expired.

All lifecycle operations serialize through the same job-row lock used by `hire_application`. Thus a manual close, deadline close, and hire cannot make conflicting updates concurrently. Whichever valid transaction obtains the lock first commits; subsequent operations re-read the committed job state and enforce their own preconditions. Any failure, including an audit insert failure, aborts the entire function transaction.

The existing trusted operations already provide the closed-job invariant: submission requires an open job and future deadline; normal recruiter advancement only permits rejection once closed; interview scheduling requires open; and hiring requires open. Capacity-based closure from Phase 2D-4 remains unchanged and records `job_auto_closed`.

All three functions are `SECURITY DEFINER` solely to support the trusted service-role boundary, use `search_path = ''`, schema-qualify database objects, revoke `PUBLIC`, `anon`, and `authenticated`, and grant only `service_role`. The future FastAPI layer must verify that the authenticated JWT subject equals the supplied `admin_id` before calling either admin RPC. No API, RLS policy, scheduler, UI, n8n workflow, or notification delivery is added in this phase.
