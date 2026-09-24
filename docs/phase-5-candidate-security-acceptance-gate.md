# Phase 5 Candidate security and acceptance gate

## Candidate API inventory and authorization

All Candidate APIs require `require_candidate`: profile read/update; CV list/upload/signed access; job list/detail; application submission; application list/detail; and withdrawal. Candidate identity always comes from `CurrentUser.user_id`. Candidate request schemas reject privileged body fields where a body is accepted; query-string identity spoofing cannot alter the actor. There is no Candidate API for direct stage transitions, recruitment, notes, AI data, audits, or automation data.

Candidate response schemas intentionally expose only candidate-safe profile data, CV metadata, a 60-second signed own-CV URL response, open/future job fields, selected application CV snapshots, stage/history data, and safe interview details. They never include storage paths, recruiter IDs, recruiter notes, AI summaries/status/output, audit/outbox fields, admin creators, or service credentials.

## CV and storage security

CV upload accepts non-empty PDF data beginning `%PDF-`, with declared `application/pdf` MIME and size at most 2 MiB. Word/non-PDF, fake/empty PDF, and oversize payloads are rejected. Uploads use generated versioned `candidates/{candidate-id}/{uuid}.pdf` paths without overwrite. Fresh live storage metadata confirms `candidate-cvs` is private, permits only `application/pdf`, limits size to 2,097,152 bytes, and has zero `anon`/`authenticated` object policies. Candidate responses never expose the path; access is a 60-second signed own-CV URL. Existing live verification confirmed direct public access is not successful.

## Application transaction, snapshot, and privacy security

Application submission and withdrawal remain authoritative service-role RPC transactions. Submission atomically creates an `applied` record referencing the exact selected CV, initial history, pending AI state, two outbox events, and audit record. Duplicate active applications, non-open/expired/unavailable jobs, and foreign CVs are safely rejected. Withdrawal produces one withdrawn transition and preserves the historical row. Reapplication uses submission again—there is no special reapply endpoint—so it produces a new application ID and retains immutable CV-1/CV-2 snapshots across history.

Candidate tracking is owned-row scoped and shows historical closed/expired jobs, terminal stages, chronological safe history, and safe interview details. It does not query notes or AI summaries. Foreign and unknown application/CV access are privacy-safe. Candidate-context RLS regression checks confirm that foreign applications/CVs, notes, and AI summaries are hidden and direct application stage/CV/re-activation/insert attacks are denied.

## Privileged RPC and direct-table matrices

Fresh live function metadata covered every current public `SECURITY DEFINER` ATS RPC: recruiter assignment/unassignment, job create/edit/open/close/deadline-close, recruiter provision/deactivation, dashboard, schedule interview, recruiter transition, hire, submit, and withdraw. All use an empty search path; `PUBLIC`, `anon`, and `authenticated` cannot execute them; `service_role` can. Fresh authenticated table-privilege checks show no insert/update/delete permission for applications, history, recruiter notes, AI summaries, jobs, assignments, interviews, automation events, or audit logs.

## Acceptance mapping

| Locked test | Candidate/backend status | Future dependency |
| --- | --- | --- |
| #1 Apply/open PDF | PASS: atomic applied application, exact CV, history, AI/outbox/audit | Email delivery: Phase 8 |
| #3 Duplicate | PASS: active duplicate blocked | None |
| #5 Closed/deadline/stage attack | PASS for Candidate scope | Recruiter transitions: Phase 6 |
| #6 Withdraw/new CV/reapply | PASS | None |
| #7 File validation | PASS for Candidate PDF validation | Interview rules: Phase 7 |
| #8 Role/stage attack | PASS for Candidate/RPC scope | Recruiter assignment: Phase 6 |
| #9 Cross-Candidate privacy | PASS for Candidate scope | None |
| #10 Persistence/build | PASS for backend persistence and frontend build | Dashboard/email/mobile/UI: future phases |
| #14 AI privacy | PASS for Candidate scope | Recruiter AI/browser-key checks: Phases 6/9 |

## Verification, operational boundaries, and cleanup

Prior rollback-only live flows for Steps 1–3 verified submission, duplicate blocking, unavailable-job blocking, withdrawal, CV-1/CV-2 reapplication, independent history/artifacts, historical tracking, Candidate RLS isolation, note/AI privacy, and cleanup. The final gate refreshed storage, RPC, table-privilege, health, advisor, source/response, and secret scans. Candidate code does not call Gemini, n8n, Gmail, or SMTP; submission only writes durable pending/outbox records. No candidate frontend is implemented in this phase.

Supabase is `ACTIVE_HEALTHY`. Security-advisor notices are intentional deny-by-default RLS on internal `audit_logs` and `automation_events`; performance notices are informational unused-index observations. `backend/.env` remains ignored, and no tracked secret value, signed token, private key, or frontend backend credential was found.

The complete backend suite passed with 173 tests. The frontend production build passed. No additional acceptance test module was needed because the final gate reused and re-ran the focused, deterministic security coverage added in Steps 1–3.

Phase 6 Recruiter System is the next phase; it is not implemented by this gate.
