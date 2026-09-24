# Phase 4B: Admin Job Management

## Purpose

Phase 4B adds admin-only management of job records: create draft jobs, edit drafts, list and retrieve jobs, and transition jobs through the existing open and close lifecycle RPCs.

## Implementation

Created or modified files:

- `backend/app/schemas/admin_jobs.py`
- `backend/app/integrations/supabase_admin.py`
- `backend/app/services/admin_jobs.py`
- `backend/app/api/v1/admin_jobs.py`
- `backend/app/api/v1/router.py`
- `backend/tests/test_admin_jobs.py`

The API exposes these admin-only endpoints:

- `GET /api/v1/admin/jobs`
- `GET /api/v1/admin/jobs/{job_id}`
- `POST /api/v1/admin/jobs`
- `PATCH /api/v1/admin/jobs/{job_id}`
- `POST /api/v1/admin/jobs/{job_id}/open`
- `POST /api/v1/admin/jobs/{job_id}/close`

`JobCreate`, `JobUpdate`, and `JobResponse` use the actual jobs fields, including `application_deadline`. Request schemas forbid unknown fields, so browser requests cannot supply status, creator, closure timestamps, or actor identifiers.

Every endpoint requires `require_admin`. Mutation actor identity is always `CurrentUser.user_id`; browser-supplied IDs are neither accepted nor trusted.

## Job behavior

Draft creation uses `create_draft_job`, which sets `status = draft`, assigns `created_by` from the trusted actor, and writes the creation audit event. Draft editing uses `update_draft_job`. Because that RPC requires complete business values, the service reads the current job and merges only `JobUpdate` fields explicitly provided by the client before calling it.

Opening and closing reuse `open_job` and `close_job`; no lifecycle status is directly updated by the backend service. The database remains authoritative for deadline validity, publication completeness, capacity, lifecycle transitions, and audit entries. There is no hard-delete operation. The existing hiring rule closes a job once its openings are filled.

Service errors map to safe HTTP responses: missing jobs are 404, business or lifecycle conflicts are 409, validation is FastAPI 422, and unavailable trusted integration is 503. Raw SQL, PostgREST details, and credentials are not returned.

## Live database verification

The connected project was `ACTIVE_HEALTHY`. Its live migration history includes `admin_job_create_and_edit`.

Live catalog inspection verified these deployed signatures:

- `create_draft_job(uuid, text, text, text, job_type, text, text, timestamptz, integer)`
- `update_draft_job(uuid, uuid, text, text, text, job_type, text, text, timestamptz, integer)`
- `open_job(uuid, uuid)`
- `close_job(uuid, uuid)`

All four are `SECURITY DEFINER` functions with `search_path = ''`. `PUBLIC`, `anon`, and `authenticated` cannot execute them; only `service_role` can.

Rollback-only live SQL checks passed for active-admin create and update; candidate, recruiter, and inactive-admin rejection; forced draft status and creator; positive-opening and enum validation; one create/update audit event; failed-create atomicity (no job or audit row); draft-only updates; open, close, repeated-close idempotence, and audit behavior; expired and equal-to-current-time deadline opening denial; draft closure; and `close_expired_jobs` closure.

Separate rollback-only regression checks passed for closed-job restrictions: closed jobs block new applications, forward transitions, scheduling, and hiring while allowing rejection of an existing active application. A one-opening job auto-closed after hiring an offer-stage application, blocked a further hire, and still allowed rejection of a remaining active application. No temporary Auth users, profiles, jobs, applications, or audit rows remained after rollback.

Forced audit-insert failure was not simulated, because doing so safely would require altering production schema behavior. The verified failed-create path left no partial job or audit record.

## RLS and security regression

Live metadata confirms RLS is enabled for jobs, profiles, applications, and job-recruiter assignments. `anon` and `authenticated` have no direct insert, update, or delete privileges on those tables. The jobs read policy permits active candidates to see only open, unexpired jobs, assigned recruiters to see their jobs, and active admins to read all jobs.

The API tests also verify unauthenticated 401 behavior, candidate and recruiter 403 behavior, admin actor binding, privileged-field rejection, safe error responses, and the existing Phase 3 role authority model. Existing Phase 4A recruiter-management tests remain green.

## Verification results

- Admin-job API tests: 20 passed.
- Complete backend suite: 47 passed.
- Frontend production build: passed.
- Security advisor: two informational findings for intentionally internal RLS-protected tables (`audit_logs` and `automation_events`) with no browser policies.
- Performance advisor: 15 informational unused-index findings on the new/unused workload; no index changes were made.
- Secret scan: no token-pattern secrets found in source; `.env` is ignored and `backend/.env.example` contains placeholders only.

## Limitation and deferred work

A real Supabase access token has not been used against `GET /api/v1/auth/me`; no token-acquisition bypass was created. JWT verification, database-backed role authority, inactive-profile denial, and the API authorization matrix are covered independently.

Phase 4C recruiter-job assignment, dashboards, candidate and recruiter workflow APIs, frontend admin UI, n8n, Gemini, and email automation remain deferred.
