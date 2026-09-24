# Phase 3C — Authorization Attack Verification

The trust boundary is intact: a verified JWT subject is the only identity input, `public.profiles.role` is the only application-role source, and future RPC actors must use `CurrentUser.user_id`. Controlled tests confirm malformed, expired, wrong-key, wrong-issuer, missing-subject, and role-spoofed tokens fail safely or retain the database role. Missing and inactive profiles return 403; exact role dependencies have no hierarchy.

Phase 2E remains the direct-data defense: candidates cannot read notes or AI summaries; recruiters are assignment-scoped; exact CV snapshot access does not grant unrelated CV-version access; inactive privileged users lose access; and internal automation/audit tables remain browser-inaccessible. Phase 2D RPCs have no PUBLIC, anon, or authenticated execute privilege and retain service-role-only execution.

Authentication errors are generic 401 responses and authorization errors are concise 403 responses. Repository scanning found only placeholder configuration and intentional documentation references—no real secret, JWT, API key, or private signing material. Live token verification remains unavailable without a safe supported token-acquisition workflow; no bypass or persistent test identity was created.
