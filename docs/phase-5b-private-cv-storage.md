# Phase 5B: Private CV storage — Step 1

`20260923150000_candidate_cv_storage.sql` creates the `candidate-cvs` bucket. Live verification confirms it is private, restricts MIME type to `application/pdf`, caps objects at 2,097,152 bytes, and has no browser `anon`/`authenticated` storage-object policies. Uploads are therefore FastAPI/service-role controlled.

`POST /api/v1/candidate/cvs` requires `require_candidate` and derives ownership exclusively from `CurrentUser.user_id`. It reads at most 2 MiB plus one byte, requires non-empty declared `application/pdf` content beginning with `%PDF-`, and returns `422` for invalid input or `413` for oversize input. The browser cannot control the owner namespace or storage path.

Every valid upload generates `candidates/{candidate_id}/{server_uuid}.pdf` with no upsert/overwrite. Original filenames are retained only as sanitized metadata. The backend uploads the object first, then registers a new immutable `candidate_cvs` row. If registration fails it attempts object deletion; a cleanup failure is intentionally not leaked, so the residual risk is an orphaned private object requiring operational cleanup. Existing `(cv_id, candidate_id)` application snapshot foreign key is unchanged.

Focused upload tests: `7 passed`; full backend: `107 passed`; frontend production build: passed; Supabase: `ACTIVE_HEALTHY`. Tests use fakes and create no live objects. No signed URLs, downloads, deletion, recruiter/admin CV access, or frontend UI were added. Those are deferred to Step 2.

## Step 2: candidate signed access

`GET /api/v1/candidate/cvs/{cv_id}/access` requires `require_candidate`, loads metadata only with the authenticated `CurrentUser.user_id`, and returns a Storage signed URL valid for exactly 60 seconds with the safe CV ID and original filename. Foreign or unknown metadata is normalized to the same `404`; signing failures are a safe `503`. The client never supplies or receives `storage_path`, bucket credentials, or a permanent URL. URLs are generated on demand and never persisted or audited. The bucket remains private; recruiter and admin CV access are deferred.

Step 2B added route-level authorization/privacy tests, including candidate actor spoofing, foreign/unknown `404`, safe signing failure, response allowlist, and exact 60-second integration TTL. Full backend regression passed with `109 passed`; frontend build passed. Live bucket settings remain verified from Step 1. Live trusted signing could not be rerun because the local backend runtime has no configured Supabase URL/service credential; no temporary object was created. Real JWT endpoint testing remains deferred without introducing a bypass.

## Final live signing verification

The local backend runtime was configured with its ignored environment file and verified without printing credentials. A uniquely named synthetic PDF object was uploaded through the trusted integration, confirmed unavailable through the normal public-object route, signed with a 60-second TTL, and retrieved successfully using the temporary signed URL. The URL and token were not printed, stored, logged, or committed. The temporary object was deleted immediately and a follow-up check confirmed zero remaining verification objects.

Fresh verification confirms the bucket remains private, accepts only `application/pdf`, enforces the 2,097,152-byte limit, and has no browser storage-object policies. The complete backend suite passed with `109 passed`, frontend production build passed, Supabase is `ACTIVE_HEALTHY`, and a fresh secret scan found no credential or signed-token patterns. Live HTTP endpoint verification with a real candidate JWT remains deferred; no authentication bypass was added. Recruiter and Admin CV access remain deferred.
