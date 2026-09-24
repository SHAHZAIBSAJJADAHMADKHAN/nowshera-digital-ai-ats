# Phase 2A — Core Identity and Jobs Schema

## Tables and relationships

- `public.profiles` is the application identity record. Its primary key is also a foreign key to `auth.users.id`, creating a one-to-one relationship without storing authentication data or passwords.
- `public.jobs` stores the initial job definition and is created by a profile.
- `public.job_recruiters` is a normalized many-to-many assignment table between jobs and recruiter profiles. Its composite primary key prevents assigning the same recruiter to the same job twice.

All application foreign keys use `ON DELETE RESTRICT`. This deliberately preserves future recruitment and audit history: users and jobs should be deactivated or closed rather than silently deleting related business records.

## Controlled values and lifecycle

PostgreSQL enums provide database-level validation:

- `app_role`: `candidate`, `recruiter`, `admin`
- `job_type`: `full-time`, `part-time`, `internship`
- `job_status`: `draft`, `open`, `closed`

Jobs default to `draft`. `closed_at` is available for the future lifecycle implementation; automatic closure and application-based state transitions are intentionally not implemented in this phase.

## Timestamps and indexes

The minimal `public.set_updated_at()` trigger function updates `updated_at` on profiles and jobs. It runs with invoker security and has no public execution grant.

Indexes support expected later access patterns for active roles, job status, department, deadline, recruiter assignments, and foreign-key lookups for job creators and assignment creators.

## RLS state

RLS is enabled on all three public application tables. No policies exist yet, so direct client access is denied by default. Full Candidate/Recruiter/Admin authorization is deferred to the dedicated RLS phase.

## Deferred work

This phase does not create CV, application, history, interview, note, AI, automation, or audit tables; it also does not create users, storage buckets, APIs, frontend business pages, or authentication/RBAC logic.
