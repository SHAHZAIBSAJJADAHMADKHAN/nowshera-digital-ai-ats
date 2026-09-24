# Phase 4D: Admin dashboard

## Scope

Step 1 implements the trusted database aggregation required by the Admin Dashboard. Step 2 adds its typed FastAPI schema, trusted integration, service, and one protected route. Step 3 adds dedicated API tests and final verification. Frontend UI is not implemented yet.

## Dashboard data model

`public.get_admin_job_dashboard(p_admin_id uuid)` returns one row for every `public.jobs` record, ordered by `jobs.created_at DESC, jobs.id DESC`. Its fields are:

- `job_id`, `title`, `department`, `status`, `application_deadline`, and `openings`
- `total_applied`, `applied_count`, `shortlisted_count`, `interview_count`, `offer_count`, `hired_count`, `rejected_count`, and `withdrawn_count`

`application_deadline` is the actual stored jobs-table deadline field. Count columns are PostgreSQL `bigint` values, which are predictable numeric values for future FastAPI serialization.

`total_applied` is the number of application records for a job, including every current `public.application_stage`: `applied`, `shortlisted`, `interview`, `offer`, `hired`, `rejected`, and `withdrawn`. It is therefore the sum of all seven stage counts, not a unique-candidate count, an active-only count, or the number of openings. A withdrawn application followed by a reapplication produces two records and contributes two to `total_applied`.

Aggregation uses `public.jobs` as the base relation with a `LEFT JOIN` to `public.applications`, so draft, open, and closed jobs with no applications remain present with zero counts. Each application is counted once from its current `applications.stage`; `application_stage_history` is deliberately not queried, preventing transition-history rows from inflating dashboard counts.

## Authorization and privileges

The function is `SECURITY DEFINER` with an empty `search_path`. It checks `public.profiles` for the supplied actor ID, requiring `role = 'admin'` and `is_active = true`; it does not trust browser role claims.

Execution is revoked from `PUBLIC`, `anon`, and `authenticated`, and granted only to `service_role`. The intended future path is browser JWT → FastAPI `require_admin` → current user ID → trusted service-role integration → RPC. Browsers cannot invoke this privileged RPC directly.

## Query and index strategy

The RPC executes one set-based `LEFT JOIN` and uses `COUNT(...) FILTER (WHERE ...)` expressions for the seven current stages. It does not make per-job or per-stage queries. Existing `applications_job_id_idx` supports the join and `applications_stage_idx` already exists. No counter table, duplicated count column, or speculative index was added.

## Migration

`supabase/migrations/20260923140000_admin_job_dashboard.sql` creates the function and its service-role-only privileges. It was deployed to the connected project as remote migration `admin_job_dashboard`.

## Live verification

Rollback-only fixtures verified all of the following:

- Active admin access; candidate, recruiter, inactive-admin, and missing-actor denial.
- Draft, open, and closed jobs are returned.
- A zero-application draft job has all eight counts at zero.
- One application in each stored stage returns `total_applied = 7` and every stage count equal to one, even with two stage-history rows for one application.
- A closed job containing hired, rejected, and withdrawn applications returns total three and those three stage counts equal to one, with all other stage counts zero.
- A withdrawn application followed by a new applied application for the same candidate returns total two, withdrawn one, and applied one.
- Two successive executions return the same aggregate output.
- Count type is `bigint`.
- Live function metadata confirms `SECURITY DEFINER`, empty search path, no execute privilege for `PUBLIC`/`anon`/`authenticated`, and execute privilege for `service_role`.

All fixture operations were rolled back. Follow-up cleanup checks found zero fake auth users, profiles, jobs, applications, stage-history records, and audit/outbox data.

## Regression and platform health

The backend suite passed with `71 passed`. The connected Supabase project remained `ACTIVE_HEALTHY`. Advisors report only the existing informational findings: two internal RLS-enabled tables without browser policies (`audit_logs`, `automation_events`) and unused-index notices; no unrelated changes were made.

## Step 2: FastAPI layer

Step 2 adds the smallest trusted FastAPI path over the Step 1 RPC:

- `backend/app/schemas/admin_dashboard.py` defines `AdminJobDashboardResponse` with the exact RPC fields. PostgreSQL `bigint` counts are parsed as JSON integers, reject negative values, and must satisfy `total_applied = applied + shortlisted + interview + offer + hired + rejected + withdrawn`.
- `SupabaseAdminClient.get_admin_job_dashboard` makes one service-role request to `get_admin_job_dashboard(p_admin_id)`. It does not query jobs, applications, or stage history separately.
- `AdminDashboardService.get_job_dashboard` passes through RPC ordering, validates each trusted record, and converts malformed/non-list/integration failures into a normalized dashboard-operation failure.
- `GET /api/v1/admin/dashboard/jobs` is registered once and protected with `require_admin`. It passes only `CurrentUser.user_id` to the service; it accepts no browser-controlled actor identifier.

An empty RPC result is returned as `200 []`. Zero-application job rows are not filtered. Integration or invalid trusted-result failures map to safe `503 Dashboard service is unavailable` responses without exposing Supabase details. The endpoint is a one-RPC/no-N+1 read.

Frontend dashboard UI is not implemented yet.

## Step 3: final verification

`backend/tests/test_admin_dashboard.py` adds 13 mocked FastAPI/service tests. They cover unauthenticated `401`, candidate and recruiter `403`, active-admin `200`, `CurrentUser.user_id` actor binding despite an `admin_id` query-string spoof attempt, empty `200 []`, zero-application rows, exact response fields, all seven stage counts, withdraw/reapply representation, integer serialization, negative/float/inconsistent trusted-count rejection, safe `503` behavior, and one integration call per dashboard retrieval.

The response model rejects negative counts and non-integer values, and enforces the total/stage invariant. The router exposes no browser-controlled actor input and continues to use a single trusted RPC; it never reads stage history or performs N+1 job/stage queries.

### Live database regression

Rollback-only fixtures re-verified live function metadata (`SECURITY DEFINER`, empty search path, `PUBLIC`/`anon`/`authenticated` no execute, `service_role` execute). Active admin access succeeded; candidate, recruiter, inactive admin, and missing actor access were rejected.

The fixtures verified draft, open, and closed dashboard rows; a zero-application job with every count zero; one mixed open job with all seven current stages and total seven; and a withdrawn-plus-reapplied candidate with total two, applied one, and withdrawn one. Two consistent stage-history rows for an interview-stage application did not inflate counts. Repeated unchanged reads were stable. A real trusted recruiter transition from `applied` to `shortlisted` was then executed inside the transaction, and the next dashboard call reflected the persisted current stage, proving refresh behavior without a cache.

All fixture writes were rolled back. Follow-up checks found zero temporary auth users, profiles, jobs, recruiter assignments, applications, CV metadata, stage-history rows, interviews, AI summaries, automation events, and audit rows.

### Regression and security finalization

- Dedicated dashboard suite: `13 passed`.
- Phase 3, 4A, 4B, and 4C regression selection: `63 passed`.
- Complete backend suite: `84 passed` (one unrelated dependency deprecation warning).
- Frontend production build: passed; no dashboard UI was added.
- Supabase project: `ACTIVE_HEALTHY`.
- Advisors: only the existing informational RLS-without-browser-policy findings for internal `audit_logs` and `automation_events`, plus existing unused-index notices; no unrelated database changes were made.
- Secret checks: `backend/.env` is ignored, `.env.example` contains placeholders only, and source scans found no service-role secret, JWT, refresh token, password, private key, invitation token, or Gemini/API key. The frontend contains no backend-secret references.

No real user JWT was acquired or used for endpoint verification, to avoid creating accounts, invitations, or a bypass. This is not a Phase 4D blocker: existing JWT/profile/role tests, route authorization tests, and independent database RPC authorization are all verified. A real-token endpoint smoke test remains deferred for an authorized environment.

Phase 4D is complete. The next scoped work, when requested, is the frontend Admin Dashboard UI; Phase 5 has not been started.
