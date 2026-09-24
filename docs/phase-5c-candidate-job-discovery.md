# Phase 5C: Candidate job discovery

Phase 5C reuses the existing `public.jobs` schema and adds no migration. It provides `GET /api/v1/candidate/jobs` and `GET /api/v1/candidate/jobs/{job_id}`. Both routes require an active Candidate through `require_candidate`; there is no candidate ID input and a `candidate_id` query parameter cannot change the actor or visibility.

The trusted backend discovery integration selects only `status = open` jobs with `application_deadline >` its authoritative request-time UTC timestamp. The existing Phase 2E Candidate RLS policy independently uses the same availability rule against database `now()`: `status = 'open' and application_deadline > now()`. Therefore a deadline equal to the relevant authoritative current time is unavailable. No filters or pagination were introduced.

List output is deliberately limited to `id`, `title`, `department`, `location`, `job_type`, `application_deadline`, and `openings`. Detail output adds only `description`, `requirements`, and `created_at`. It never returns `created_by`, `closed_at`, recruiter assignments or IDs, audit data, or other internal lifecycle fields. The list is ordered by `application_deadline ASC, id ASC` and bounded to 100 records. A hidden, expired, closed, draft, or unknown detail is normalized to the generic `404 Job not found`; trusted-integration failures are normalized to `503 Candidate job discovery is unavailable` without exposing integration details.

## Verification and closure

- Dedicated HTTP/integration tests: 16 passed. They cover unauthenticated, recruiter, admin, and Candidate route access; list/detail safe shapes; empty results; generic hidden detail 404s; malformed IDs; deterministic order; `limit=100`; the open/future predicates; query spoofing; and error-detail redaction.
- Live database matrix: rollback-only synthetic Draft/future, Open/future, Closed/future, Open/past, and Open/deadline-equal-to-database-`now()` jobs were created. The trusted discovery equivalent query returned only Open/future.
- Candidate-context RLS: in the same rollback-only transaction, the project’s authenticated role plus controlled Candidate JWT-claim simulation returned only the Open/future job. Draft, Closed, expired Open, and deadline-equality rows were not directly visible. No bearer-token or auth bypass was created.
- Consistency: the backend predicate and Candidate RLS agree on open, strictly future visibility. `submit_application` uses the same `status = 'open'` and `application_deadline > now()` eligibility check (and adds capacity validation), so discovery does not advertise a job unavailable solely due to state or deadline.
- Lifecycle regression: the existing `open_job`, `close_job`, `close_expired_jobs`, and hire auto-close coverage remains in the full backend suite; discovery only reads state and changed none of those lifecycle functions.
- Cleanup: all live fixtures were inserted inside an explicit transaction and rolled back. A subsequent synthetic-ID check found zero jobs or profiles; no assignments, applications, audit records, or automation events were created.
- Full backend suite: 125 passed. Frontend production build: passed. Supabase project health is `ACTIVE_HEALTHY`. Advisor results are the pre-existing informational deny-by-default RLS notices for internal `audit_logs` and `automation_events`, plus informational unused-index findings; no schema changes were made.
- Secret scan: `backend/.env` remains ignored and untracked; `.env.example` is placeholder-only. The scan found no credential material in tracked source. Literal secret-marker strings used by redaction tests and intentional `service_role` grants in migrations are not secrets.

The only remaining limitation is that no real end-user Candidate bearer token was used for this verification; the live Candidate RLS test used the project’s controlled database role/JWT-claim technique. Candidate application submission/API work remains deferred to Phase 5D.
