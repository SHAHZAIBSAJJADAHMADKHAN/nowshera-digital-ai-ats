# Phase 3A — FastAPI Supabase JWT Authentication

FastAPI verifies Bearer access tokens against the connected Supabase Auth issuer (`<SUPABASE_URL>/auth/v1`) and JWKS endpoint (`<SUPABASE_URL>/auth/v1/.well-known/jwks.json`). The connected project currently publishes an ES256 signing key, and the verifier permits only ES256 or RS256 with a `kid`; it never decodes an unverified payload as identity.

JWKS is cached for five minutes and refreshed once immediately for an unknown `kid`, supporting ordinary key rotation without a per-request network fetch. Signature, issuer, expiry, algorithm, key ID, and non-empty subject are required. Audience is intentionally not enforced in this phase because no stable project access-token audience has been configured/confirmed.

`AuthenticatedPrincipal` contains the verified subject, optional email, token role, and claims. `/api/v1/auth/me` returns only `user_id` and `email`. Missing, malformed, expired, wrong-issuer, wrong-key, or unsupported tokens return a generic 401 without cryptographic details.

Only URL, issuer, JWKS URL, and publishable-key placeholders belong in configuration. Secret/service-role credentials remain backend-only and are never returned. Role/profile loading and authorization are explicitly deferred to Phase 3B.
