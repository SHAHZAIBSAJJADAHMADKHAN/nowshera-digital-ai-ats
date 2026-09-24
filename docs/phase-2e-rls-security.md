# Phase 2E — RLS and Database Privacy

All ATS tables remain RLS-enabled. Browser sessions receive read-only table privileges and no browser `INSERT`, `UPDATE`, or `DELETE` privileges. `anon` receives no ATS table access. Trusted Phase 2D RPCs remain service-role-only and are not browser RPCs.

| Resource | Candidate | Assigned active recruiter | Active admin | Internal service |
| --- | --- | --- | --- | --- |
| Profiles | Own active profile | Own active profile only | All profiles | Trusted access |
| Jobs | Open and unexpired only | Assigned jobs only | All jobs | Trusted access |
| Assignments | None | Own assignment rows | All rows | Trusted access |
| CV metadata | Own rows | Exact CV snapshots on assigned applications | All rows | Trusted access |
| Applications/history/interviews | Own application rows | Assigned-job rows | All rows | Trusted access |
| Recruiter notes | None | All notes on assigned applications | None | Trusted access |
| AI summaries | None | Assigned-job rows | All rows | Trusted access |
| Automation events/audit logs | None | None | None | Trusted access |

The private-schema, `SECURITY DEFINER`, `STABLE` helpers query profiles and assignment records without recursive profile policies. They expose only authorization booleans to RLS expressions: active user, candidate, admin, assigned recruiter, authorized application participant, and exact CV snapshot access. They use an empty search path, schema-qualified relations, have no `PUBLIC`/`anon` execute rights, and are only executable by `authenticated` policy evaluation. They are not in the exposed `public` schema.

Identity always derives from `(select auth.uid())`; role, activity, candidate ID, and recruiter assignment are database facts, never browser input. Inactive candidates have no protected reads; inactive recruiters lose assigned-work visibility; inactive admins lose administration visibility.

Candidate job visibility requires `status = open` and `application_deadline > now()`, so an expired but not-yet-synchronized open job remains hidden. Direct mutations stay unavailable, preserving the Phase 2D state machines, audit records, and outbox writes. Candidate CV visibility is ownership-only; recruiter visibility is tied to a matching application CV snapshot, not the candidate's other CV versions.

Recruiter notes use a collaborative recruiting-team model: every currently assigned active recruiter may read notes on that job's applications. Candidates and admins receive no direct note access. Automation events and audit logs intentionally have no browser policies. Storage object/bucket policies, browser APIs, and scheduler work remain deferred.
