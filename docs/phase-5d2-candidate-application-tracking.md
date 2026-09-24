# Phase 5D Step 2: Candidate application tracking

This read-only step adds `GET /api/v1/candidate/applications` and `GET /api/v1/candidate/applications/{application_id}`. Both require `require_candidate` and scope every trusted query with `CurrentUser.user_id`; no `candidate_id` input exists. Foreign and unknown application details are both normalized to `404 Application not found`.

The bounded list is a single set-oriented trusted query, ordered `applied_at DESC, id DESC` with a maximum of 100 records. It returns application ID, current `applications.stage`, `applied_at`, safe job summary fields, and the exact `applications.cv_id` snapshot metadata. It does not filter on job state or deadline, so closed/expired jobs and applied, shortlisted, interview, offer, hired, rejected, and withdrawn applications remain in history. Multiple applications for one job remain separate records, supporting later withdrawal/reapplication history.

Detail returns the same application fields plus safe job description/requirements, exact submitted CV metadata, chronological stage history (`to_stage` as `stage`, `changed_at`), and nullable interview `starts_at`, `ends_at`, `location`, and `meeting_link`. The current stage always comes from `applications.stage`, never inferred from history. CV access remains separate: the response returns only the safe CV ID; the existing Phase 5B signed-access endpoint handles access. No storage path or signed URL is returned.

Neither query selects `recruiter_notes` or `ai_summaries`. The schemas omit recruiter identifiers, recruiter notes, AI status/prompt/output, audit data, automation events, other Candidate data, internal creator data, and storage paths.

## Verification

- Focused API tests: 21 passed. They cover authentication, Candidate-only access, actor spoofing, all stages, historical closed/expired job visibility, distinct reapplication records, deterministic list behavior and bound, safe response allowlists, exact snapshot output, chronological history, nullable/safe interview data, foreign/unknown 404s, malformed UUIDs, no private query selection, and safe 503 normalization.
- Rollback-only live verification created Candidate A/B applications, CV-1 and later CV-2 for Candidate A, closed and expired jobs, terminal stages, stage history, interview, recruiter note, and pending AI summary. Candidate A saw only its five records; Candidate B was hidden. CV-1 remained attached to the original application, terminal/closed/expired records remained visible, and reapplication records stayed distinct.
- Candidate-context RLS allowed Candidate A to read its own applications, history, interview, and snapshots, while denying Candidate B’s application, recruiter notes, AI summaries, and direct stage updates. No RLS or privilege change was made.
- All fixtures were rolled back. Follow-up verification found zero temporary profiles, jobs, CV metadata, applications, histories, interviews, notes, AI summaries, events, or audit rows.
- Supabase is `ACTIVE_HEALTHY`. Advisors report only existing informational deny-by-default RLS notices for internal audit/outbox tables and unused-index observations. `backend/.env` remains ignored and the secret-value scan is clean.
- Complete backend suite: 161 passed. Frontend production build: passed.

Withdrawal, reapply, and every other tracking mutation remain deferred to Phase 5D Step 3.
