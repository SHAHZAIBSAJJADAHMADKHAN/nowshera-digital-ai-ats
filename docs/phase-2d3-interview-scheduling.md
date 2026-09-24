# Phase 2D-3 — Interview Scheduling

`schedule_interview` is a service-role-only, SECURITY DEFINER transaction. It validates an active assigned recruiter, locks the application, requires `shortlisted` and an open job, rejects nonfuture starts, normalizes blank location/link values, and derives `ends_at` as exactly one hour later.

It atomically inserts the interview, sets `shortlisted → interview`, appends stage history, queues `interview-invitation:<interview-id>`, and appends an audit entry. Existing unique application and recruiter range-exclusion constraints remain the final authority for repeated requests and overlap races. FastAPI must validate JWT subject equals the recruiter ID before calling this trusted operation.

Interview rescheduling, hiring, capacity consumption, job auto-close, APIs, and RLS policies remain deferred.
