-- Phase 2B follow-up: cover the composite CV snapshot foreign key.

create index applications_cv_id_candidate_id_idx
  on public.applications (cv_id, candidate_id);
