# Phase 7A — Recruiter Interview Scheduling

`POST /api/v1/recruiter/applications/{application_id}/interview` delegates scheduling to `public.schedule_interview(recruiter_id, application_id, starts_at, location, meeting_link)`. The strict request accepts only `starts_at`, optional `location`, and optional `meeting_link`; `CurrentUser.user_id` supplies the recruiter actor.

The authoritative RPC requires an active assigned recruiter, a Shortlisted application, an open job, a future start, and a nonblank location or meeting link. It derives `ends_at = starts_at + interval '1 hour'`, creates the interview, moves the application to Interview, records Shortlisted→Interview history, creates the `interview_invitation` outbox event with `interview-invitation:<interview-id>`, and writes audit data.

The database exclusion constraint is recruiter-specific and uses a half-open time range: overlapping intervals for one recruiter are blocked, adjacent intervals are allowed, and different recruiters may schedule at the same time. The generic Stage API still rejects `interview`, ensuring the schedule RPC is the only route to Interview.

The RPC is service-role-only; browser roles cannot execute it directly or update interview/application state. Focused Phase 7A tests: 4 passed. Phase 6C regression: 16 passed. Complete backend suite: 221 passed. Frontend production build: passed. Secret scan is clean and `backend/.env` remains ignored and untracked.

Live verification: **PASS**. Connected Supabase transactional SQL verified valid physical-location and meeting-link scheduling, exact one-hour duration, history, invitation outbox, past-time denial, same-recruiter overlap denial, adjacent scheduling, different-recruiter same-time scheduling, unassigned denial, duplicate/wrong-stage denial, RPC security, and direct-mutation denial. The transaction rolled back with zero temporary data. No external email, n8n, Gemini, or AI retry execution occurred.
