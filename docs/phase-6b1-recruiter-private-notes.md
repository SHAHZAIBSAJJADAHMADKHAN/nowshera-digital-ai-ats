# Phase 6B Step 1 — Recruiter Private Notes

This step adds only recruiter note reading and creation:

- `GET /api/v1/recruiter/applications/{application_id}/notes`
- `POST /api/v1/recruiter/applications/{application_id}/notes`

The existing `recruiter_notes` RLS policy establishes a collaborative privacy model: every active recruiter currently assigned to the application's job can read that job's notes. Candidate and admin contexts have no policy granting note reads, and the recruiter routes require the recruiter role without introducing a role hierarchy.

The API uses `CurrentUser.user_id` as the only note author source. The request contains only `content`; it rejects extra fields, empty and whitespace-only content, and content longer than 5,000 characters. Responses contain only `id`, `content`, and `created_at`.

Reads revalidate the current `job_recruiters` assignment before fetching notes and return the same privacy-safe 404 for an unknown or inaccessible application. Historical applications remain eligible because neither the RLS policy nor the note RPC excludes terminal application stages.

Creation uses `public.add_recruiter_note(recruiter_id, application_id, note)`, a `SECURITY DEFINER` transaction with an empty search path. It locks and verifies the active recruiter profile, application, and current job assignment before inserting. The function is unavailable to `PUBLIC`, `anon`, and `authenticated`, and is executable only by `service_role`; this prevents a separate check/insert race and makes unassignment take effect immediately for writes. Browser RLS remains read-only.

No AI endpoints, Gemini/n8n calls, AI retries, stage transitions, interviews, hiring, or frontend work are included in this step.

Focused notes tests: 15 passed. The combined Phase 6B closure attempted a fresh rollback-only R1/R2/C1/J1/J2/A1/A2 fixture but the configured Supabase service credential was denied table access before profile creation. The repository now includes the scoped service-role table-grant migration required to restore the trusted FastAPI path. The live notes recheck, including author binding and unassignment write revocation, must be rerun after that migration is deployed. No temporary data was left behind.
