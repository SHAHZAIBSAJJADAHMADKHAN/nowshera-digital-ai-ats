# Phase 5A: Candidate profile and CV foundation — Step 1

## Scope

This step establishes candidate self-service profile and CV-metadata reads only. It does not implement CV upload, Storage, signed URLs/downloads, deletion, job discovery, application submission, withdrawal/reapply, automation, or frontend UI.

## Existing schema and architecture

No migration was needed. `public.profiles` already provides the required application profile fields: `id`, `full_name`, nullable `phone`, persistent lowercase `email`, `role`, `is_active`, `created_at`, and `updated_at`. Supabase Auth remains the authentication identity; `public.profiles` remains the application profile and role authority. Passwords and tokens are not stored in profiles.

Email is already persistent in `public.profiles`, is unique, and is synchronized as part of the existing profile architecture. The candidate API returns the candidate's own email but does not support email or Auth-account changes. `full_name` and `phone` are the only editable fields; no unrelated personal fields were added.

`public.candidate_cvs` already implements immutable versioned CV metadata: `id`, `candidate_id`, `storage_path`, `original_filename`, `mime_type`, `file_size_bytes`, and `uploaded_at`. `public.applications` preserves the exact submitted snapshot through its immutable `(cv_id, candidate_id)` foreign key to `candidate_cvs(id, candidate_id)`. Applications do not point at a mutable current-CV field, and this step neither updates nor deletes CV records.

## APIs and authorization

- `GET /api/v1/candidate/profile`
- `PATCH /api/v1/candidate/profile`
- `GET /api/v1/candidate/cvs`

Every route requires `require_candidate`. The authoritative owner is always `CurrentUser.user_id`; no route accepts a candidate, user, or profile ID as an authority input. Candidate profile PATCH uses the explicit `full_name`/`phone` allowlist and rejects empty, unknown, and privileged fields such as `id`, `role`, `is_active`, `email`, and timestamps.

The profile response exposes only `id`, `full_name`, `email`, `phone`, `created_at`, and `updated_at`. CV metadata returns only `id`, `original_filename`, `mime_type`, `file_size_bytes`, and `uploaded_at`; it deliberately omits `candidate_id` and private storage paths.

The service-role integration is scoped with the authenticated candidate ID for every profile/CV operation. It uses explicit selected columns, normalizes failures to safe `503` responses, and does not expose database, PostgREST, URL, or secret details. Empty CV history returns `200 []`.

## RLS and security

Existing candidate CV RLS was retained without alteration. Live inspection confirms RLS is enabled, `authenticated` has select access, and policy `candidate_cvs: exact authorized snapshots only` uses `private.can_access_cv_snapshot(id, candidate_id)`. The immutable application CV-snapshot foreign key remains in place.

## Verification

`backend/tests/test_candidate_profile.py` adds 16 focused tests covering unauthenticated and non-candidate denial, own-profile reads, actor spoof resistance, allowed updates, mass-assignment rejection, own CV metadata, empty lists, and safe errors. The full backend suite passed with `100 passed`; the frontend production build passed without adding a candidate UI. The connected Supabase project remains `ACTIVE_HEALTHY`.

No live candidate profile or CV data was created. Real JWT endpoint smoke testing remains deferred for an authorized environment; no authentication bypass was introduced.

Secret scanning found no service-role key, JWT, refresh token, password, private key, or Gemini/API key. `backend/.env` remains ignored and `.env.example` contains placeholders only.

## Deferred to Phase 5B

Phase 5B will implement private PDF Storage, PDF and size validation, versioned upload/replacement, signed access, and storage/database compensation. No upload endpoint or Storage bucket was created in this step.
