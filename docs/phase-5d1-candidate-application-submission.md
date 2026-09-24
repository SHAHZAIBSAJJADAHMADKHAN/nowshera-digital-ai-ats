# Phase 5D Step 1: Candidate application submission

`POST /api/v1/candidate/jobs/{job_id}/applications` is the submission-only Candidate API. It requires `require_candidate`; the Candidate actor is always `CurrentUser.user_id`. Its strict request body accepts only `cv_id` (UUID), rejecting candidate IDs, stages, statuses, notes, timestamps, and other unknown fields.

The endpoint calls the existing trusted service-role `public.submit_application(p_candidate_id, p_job_id, p_cv_id)` RPC exactly once. FastAPI does not reimplement application inserts, stage history, AI state, outbox, audit, duplicate, deadline, job-state, capacity, or CV-ownership business logic. The RPC returns the application UUID; the trusted backend then reads that result by ID and authenticated Candidate ID solely to return `id`, `job_id`, `cv_id`, `stage`, and `applied_at`.

Successful submissions begin at `applied`. The database stores the exact selected `cv_id` via the immutable `(cv_id, candidate_id)` snapshot foreign key; later CV uploads cannot change an existing application. The same transaction creates exactly one initial `applied` history row, one pending AI summary record, one `application_received` outbox event, one `ai_summary_requested` outbox event, and one audit record. It neither executes AI nor sends email, so those later workflows cannot block submission.

The API maps the active-application unique violation to `409 You already have an active application for this job.`. Job state, expired deadline, and capacity check violations map to `409 This job is not available for applications.`. Foreign or unknown CV foreign-key failures map to the privacy-safe `404 Selected CV is not available.`; no ownership detail is exposed. Unexpected integration failures map to a generic 503 response without SQL, PostgREST, credential, URL, or stack-trace leakage. The database remains the authoritative deadline and transaction boundary.

## Verification

- Focused FastAPI tests: 15 passed. They cover authentication and Candidate-only access; authenticated actor binding despite query spoofing; strict request fields; safe success output; duplicate, unavailable, foreign/unknown-CV, and safe-503 error mapping.
- Live rollback-only transaction verification created synthetic admin, Candidate A/B, jobs, and CV metadata. Candidate A submitted against an open future job using CV-1. The resulting row was `applied`, retained CV-1 after CV-2 existed, and had exactly one history row, pending AI record, both expected one-count outbox events, and one audit record.
- The duplicate Candidate A/job attempt was blocked. Draft, closed, and expired jobs were blocked. Candidate A using Candidate B's CV was blocked. Failed attempts created no success artifacts.
- Candidate-context RLS regression confirmed direct arbitrary application insert and stage update are denied; Candidate A cannot see Candidate B's application, recruiter notes, or AI summaries. No RLS or privilege changes were made.
- All synthetic rows were created in one explicit transaction and rolled back. Follow-up cleanup found zero temporary profiles, jobs, CV metadata, applications, history rows, AI summaries, automation events, and audit rows.
- Live function metadata confirms `submit_application` remains `SECURITY DEFINER` with empty `search_path`; `PUBLIC`, `anon`, and `authenticated` cannot execute it, while `service_role` can.
- Complete backend suite: 140 passed. Frontend production build: passed. Supabase: `ACTIVE_HEALTHY`. Fresh secret-value scan: clean; `backend/.env` remains ignored and no tracked secret values were found.

Application listing/detail, withdrawal/reapply, and all Candidate application discovery are deferred to Phase 5D Step 2.
