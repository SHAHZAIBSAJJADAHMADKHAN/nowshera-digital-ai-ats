# Phase 6B — Recruiter Review Security Gate

## Current closure decision: NEEDS ATTENTION — one safe historical verification remains

Phase 6B combines private recruiter notes (Step 1) with read-only recruiter AI summaries (Step 2). The implementation is deliberately limited to the existing notes `GET`/`POST` routes and `GET /api/v1/recruiter/applications/{application_id}/ai-summary`; retry execution remains deferred to Phase 9.

## Implemented security boundary

Notes use a collaborative, currently assigned-recruiter model. The request body cannot supply an author: FastAPI binds the author to `CurrentUser`, and the atomic `add_recruiter_note` RPC locks and rechecks the current assignment. Its `SECURITY DEFINER` function has an empty search path and is denied to `PUBLIC`, `anon`, and `authenticated`; only `service_role` can execute it. Candidate and admin callers receive `403` on recruiter routes, and unassignment is intended to revoke notes reads and writes immediately.

AI summaries are read through the exact application route only. Supported persisted statuses are `pending`, `processing`, `completed`, and `failed`; a missing row maps to `unavailable`. All responses are marked `is_ai_generated`. Only completed state exposes the three structured output groups: 3–5 profile bullets, requirements found/not found, and exactly three interview questions. The allowlisted response excludes CV text, prompts, provider payloads/errors, scores, ranks, recommendations, decisions, credentials, and automation internals. Reads do not change application stage or history. Candidate responses expose neither notes nor AI summaries.

## Verification evidence

- Focused route tests pass: notes 15; AI summary 11 (26 combined). The complete backend suite passes with 201 tests, and the frontend production build passes.
- The deployed service-role table-grant migration resolved the previous `42501` error. Service-role reads now pass for every table used by the trusted backend; the configured JWKS endpoint is reachable.
- A fully cleaned tagged R1/R2/C1/C2/J1/J2/A1/A2 fixture confirmed every persisted AI status and missing-row representation, exact application isolation, assignment matrix, direct authenticated recruiter RLS, candidate RLS denial, candidate API privacy, decision safety, no stage/history mutation, notes author binding, and immediate AI/notes revocation and reassignment.
- Browser-authenticated attempts to mutate `ai_summaries` and `recruiter_notes`, or invoke the note RPC directly, remain denied. No external AI, n8n, retry, email, storage, automation, or audit side effect occurred. Fixture cleanup left zero tagged Auth users, profiles, jobs, assignments, CVs, applications, history rows, notes, summaries, or storage objects.

`20260923170000_grant_service_role_backend_table_access.sql` supplies the required trusted-backend table privileges without broadening browser grants or RLS, and is deployed. The only remaining gate is the historical read: it must be created only with `submit_application` then `withdraw_application`. The available REST-only session cannot roll back the immutable audit records created by that authoritative lifecycle, so that check was not attempted.

## Required rerun gates

In a rollback-capable SQL session, run only the historical authoritative lifecycle check and confirm zero temporary data afterwards. Recheck Supabase advisors and RPC metadata in that same authenticated database session if management access is available.

## Static checks retained for the rerun

Routes are registered once each: notes `GET`/`POST`, AI summary `GET`; no AI retry route exists. Migrations retain assignment-scoped recruiter RLS for `ai_summaries`, deny candidates through that policy, and preserve the service-role-only note RPC. The fresh source scan found no tracked secret material; `backend/.env` remains ignored and untracked, while frontend source contains no backend/AI credential.
