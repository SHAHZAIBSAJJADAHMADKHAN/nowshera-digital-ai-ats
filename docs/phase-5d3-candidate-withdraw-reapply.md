# Phase 5D Step 3: Candidate withdrawal and reapplication

This step adds the bodyless `POST /api/v1/candidate/applications/{application_id}/withdraw` endpoint. It requires `require_candidate` and supplies only `CurrentUser.user_id` and the path application ID to the existing trusted `withdraw_application` RPC. FastAPI does not update an application, create history, or write audit data directly. On success, it reads the owned row only to return the minimal `id`, `stage: withdrawn`, and `withdrawn_at` response.

The existing database state machine permits withdrawal from `applied`, `shortlisted`, `interview`, and `offer`. It blocks `hired`, `rejected`, and already `withdrawn` applications. Foreign and unknown application failures share the privacy-safe `404 Application not found`; blocked terminal transitions return the stable `409 This application cannot be withdrawn.`; unexpected integration failures return a safe 503 response.

There is no reapply endpoint. Reapplication uses the existing `POST /api/v1/candidate/jobs/{job_id}/applications` submission endpoint and its `submit_application` transaction. After a withdrawal releases the active partial-unique slot, a reapplication creates a new application record and never reactivates or changes the original withdrawn row. The original row retains CV-1; the new row can use CV-2. The normal submission transaction creates the new record’s independent applied history, pending AI summary, and one each of the application-received and AI-request outbox events. Withdrawal does not invent an email or outbox event, and no AI/email execution occurs.

The same submit transaction still blocks active duplicates, closed jobs, expired deadlines, and unavailable capacity. This step changes no lifecycle, RLS, storage, or privilege rules.

## Verification

- Focused tests: 12 passed. They cover authentication, Candidate-only access, `CurrentUser` binding despite query spoofing, successful withdrawal, foreign/unknown privacy, terminal conflicts, malformed identifiers, RPC arguments, and safe 503 behavior.
- A rollback-only live core flow applied with CV-1, withdrew through the authoritative transaction, added CV-2, and reapplied through `submit_application`. Application A was withdrawn with CV-1; new Application B had a different ID, remained applied with CV-2, and both histories remained independent. Candidate tracking can represent both separately.
- The active duplicate after B was blocked. Withdraw-then-closed and withdraw-then-expired reapplications were blocked. Foreign withdrawal and hired/rejected/repeated-withdraw attempts were blocked. B had exactly one initial history record, one pending AI record, and exactly one each of its expected outbox events; A retained its historical submission events.
- Candidate-context RLS still denies direct stage/CV changes and arbitrary application inserts, foreign application visibility, recruiter notes, and AI summaries.
- All synthetic rows were rolled back. Follow-up checks found zero temporary profiles, jobs, CVs, applications, histories, interviews, notes, AI summaries, events, or audits.
- Both `submit_application` and `withdraw_application` remain `SECURITY DEFINER` with an empty search path; `PUBLIC`, `anon`, and `authenticated` lack execute privilege while `service_role` retains it. Supabase is `ACTIVE_HEALTHY`.
- Complete backend suite: 173 passed. Frontend production build: passed. `backend/.env` remains ignored and the secret-value scan is clean.

Candidate frontend work and Phase 5D Step 4 remain deferred.
