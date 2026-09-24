# Phase 3B — Profile Binding and Role Authorization

Phase 3A verifies a JWT. Phase 3B binds its verified `sub` to `public.profiles.id` through a backend-only service-key repository. `CurrentUser.user_id` always comes from the verified subject; role and active state come only from the profile row. Missing, inactive, malformed, or unsupported profiles fail closed with 403.

`require_candidate`, `require_recruiter`, and `require_admin` are exact-role dependencies—there is no implicit hierarchy. `/api/v1/auth/me` now returns verified user ID/email plus authoritative role and active state. Future trusted RPC calls must use `CurrentUser.user_id`, never an actor ID supplied by the browser.

The service/secret key is read only from ignored backend configuration, remains inside `ProfileRepository`, and is never returned or logged. Unit tests replace the repository; live verification remains deferred until a safe test-token workflow exists. Phase 3C business APIs and all profile provisioning remain deferred.
