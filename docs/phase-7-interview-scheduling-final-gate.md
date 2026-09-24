# Phase 7 — Interview Scheduling Final Gate

## Result: PASS

The dedicated endpoint is `POST /api/v1/recruiter/applications/{application_id}/interview`. It binds the actor to `CurrentUser.user_id`, requires the recruiter role, uses a strict scheduling body, and leaves lifecycle authority to `public.schedule_interview(recruiter_id, application_id, starts_at, location, meeting_link)`.

The RPC revalidates assignment and requires a Shortlisted application, future time, and a location or meeting link. It derives an exact one-hour end time, creates the interview, records Shortlisted→Interview history, emits one `interview_invitation` outbox event, and records audit data. Its recruiter-specific half-open exclusion constraint blocks overlap, allows adjacent interviews, and permits different recruiters at the same time. Generic stage PATCH still excludes `interview`.

Connected Supabase transactional SQL passed valid scheduling, physical-location and meeting-link cases, future-time denial, overlap/adjacent/different-recruiter behavior, wrong-stage and duplicate denial, unassigned denial, outbox/history verification, privilege checks, and rollback cleanup. No external email, n8n, Gemini, or retry execution occurred; temporary data remaining was zero.

Automated evidence: Phase 7A focused tests 4 passed; Phase 6C regression 16 passed; complete backend suite 221 passed; frontend build passed. Browser roles cannot invoke the privileged scheduling RPC, insert interviews, or update application stage directly.

Phase 7 supplies the Shortlisted→Interview component of Acceptance Test #2, overlap/past-time coverage for Acceptance Test #7, and unassigned/candidate mutation protection for Acceptance Test #8. Phase 8 remains responsible for external invitation delivery.
