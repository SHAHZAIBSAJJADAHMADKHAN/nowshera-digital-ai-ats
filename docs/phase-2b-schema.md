# Phase 2B — CVs, Applications, History, and Recruiter Notes

## CV versioning and application snapshot

`candidate_cvs` stores immutable metadata for each PDF upload; the file itself will later be placed in private Supabase Storage. CV rows cannot be updated, so a replacement is always a new version.

`applications` references `(cv_id, candidate_id)` through a composite foreign key to `candidate_cvs`. This proves the submitted CV belongs to the application candidate and permanently identifies the exact version used at submission. An application update trigger prevents changing its candidate, job, CV snapshot, or `applied_at` after creation.

## Stages and active-application rule

`application_stage` is a PostgreSQL enum: `applied`, `shortlisted`, `interview`, `offer`, `hired`, `rejected`, and `withdrawn`.

The partial unique index on `(candidate_id, job_id)` applies only to `applied`, `shortlisted`, `interview`, and `offer`. These are active stages that occupy a candidate's application slot for a job. `withdrawn`, `rejected`, and `hired` are terminal historical stages, so they do not block a later application. This enables reapplication after withdrawal while preserving the older application's CV snapshot.

`withdrawn_at` is required exactly when stage is `withdrawn`.

## History and notes

`application_stage_history` supports later auditable transitions, including the initial `NULL → applied` event. Stage transition rules and automatic history creation are deferred to Phase 2D.

`recruiter_notes` holds nonblank internal notes. It is RLS-enabled with no policies, so it is private by default. The future RLS design will limit it to assigned recruiters and authorized admins; candidates will receive no access.

## Delete and security posture

All new foreign keys use `ON DELETE RESTRICT` to retain recruitment history and CV references. Indexes cover the composite CV-snapshot foreign key and expected candidate, job, stage, history, and note lookups. RLS is enabled on every new public table without permissive temporary policies.

## Deferred work

This phase does not create Storage buckets or policies, APIs, UI pages, interview/AI/automation/audit tables, Auth users, complete stage-transition logic, profile-role actor validation, or job-open checks during application submission. Those transactional business rules belong to later phases.
