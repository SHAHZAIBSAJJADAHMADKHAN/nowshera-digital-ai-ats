import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { CalendarClock, FilePlus2, FileText, RefreshCw, Sparkles, Users } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { adminService as S } from "../services/adminService";
import { adminDetailSummary, adminInterviewLabel } from "../adminApplicationView";

const fmt = d => d ? new Date(d).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }) : "—";
const fmtTime = d => d ? new Date(d).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : "—";
const Status = ({ value }) => <span className={`admin-status admin-status--${value}`}>{value}</span>;
const Load = () => <p className="admin-state" role="status">Loading management data…</p>;
const Err = ({ children }) => <p className="admin-error" role="alert">{children}</p>;

function Dialog({ children, onClose }) {
  useEffect(() => {
    const close = e => e.key === "Escape" && onClose();
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [onClose]);
  return <div className="admin-dialog-backdrop"><section className="admin-dialog" role="dialog" aria-modal="true"><button className="admin-dialog-close" aria-label="Close dialog" onClick={onClose}>×</button>{children}</section></div>;
}

export function AdminAssignments() {
  const { token } = useAuth(), [jobs, setJobs] = useState(), [recruiters, setRecruiters] = useState(), [jobId, setJobId] = useState(""), [assigned, setAssigned] = useState(), [recruiterId, setRecruiterId] = useState(""), [err, setErr] = useState(""), [msg, setMsg] = useState(""), [busy, setBusy] = useState(false), [remove, setRemove] = useState();
  useEffect(() => { Promise.all([S.jobs(token), S.recruiters(token)]).then(([j, r]) => { setJobs(j); setRecruiters(r); setJobId(j[0]?.id || ""); }).catch(e => setErr(e.message)); }, [token]);
  const load = () => jobId && S.assignedRecruiters(token, jobId).then(setAssigned).catch(e => setErr(e.message));
  useEffect(() => { setAssigned(undefined); load(); }, [token, jobId]);
  const assign = async e => { e.preventDefault(); if (!recruiterId) return setMsg("Choose an active recruiter."); setBusy(true); setMsg(""); try { await S.assignRecruiter(token, jobId, recruiterId); setRecruiterId(""); setMsg("Recruiter assigned."); await load(); } catch (x) { setMsg(x.message); } finally { setBusy(false); } };
  const unassign = async () => { setBusy(true); setMsg(""); try { await S.unassignRecruiter(token, jobId, remove.id); setRemove(null); setMsg("Recruiter unassigned."); await load(); } catch (x) { setMsg(x.message); } finally { setBusy(false); } };
  if (err) return <Err>{err}</Err>;
  if (!jobs || !recruiters) return <Load />;
  if (!jobs.length) return <div className="admin-empty"><Users /><h3>No jobs available</h3><p>Create a job before assigning recruiters.</p></div>;
  const eligible = recruiters.filter(r => r.is_active && !assigned?.some(a => a.id === r.id));
  return <><header className="admin-head"><div><p className="eyebrow">Recruiter assignments</p><h1>Connect people to hiring work.</h1><p>Assignments are backend-enforced recruiter access scope.</p></div></header><div className="admin-assignment-grid"><section className="admin-panel"><p className="eyebrow">Choose role</p><h2>Job</h2><select value={jobId} onChange={e => setJobId(e.target.value)}>{jobs.map(j => <option key={j.id} value={j.id}>{j.title} · {j.status}</option>)}</select><form className="admin-assignment-form" onSubmit={assign}><label>Active recruiter<select value={recruiterId} onChange={e => setRecruiterId(e.target.value)}><option value="">Choose recruiter</option>{eligible.map(r => <option key={r.id} value={r.id}>{r.full_name}</option>)}</select></label><button className="button" disabled={busy || !eligible.length}>{busy ? "Assigning…" : "Assign"}</button></form>{msg && <p className="admin-muted">{msg}</p>}</section><section className="admin-panel"><p className="eyebrow">Current scope</p><h2>Assigned recruiters</h2>{!assigned ? <Load /> : assigned.length ? <div className="admin-assignment-list">{assigned.map(r => <article key={r.id}><div><b>{r.full_name}</b><small>{r.email} · Assigned {fmt(r.assigned_at)}</small></div><button className="admin-action danger" onClick={() => setRemove(r)}>Unassign</button></article>)}</div> : <div className="admin-empty"><Users /><h3>No recruiters assigned</h3><p>Assign an active recruiter to grant access to this job’s applications.</p></div>}</section></div>{remove && <Dialog onClose={() => setRemove(null)}><h2>Unassign recruiter?</h2><p>This removes the recruiter’s assignment scope for the selected job. The backend confirms the change.</p><div className="admin-dialog-actions"><button className="link-button" onClick={() => setRemove(null)} disabled={busy}>Cancel</button><button className="button admin-action danger" onClick={unassign} disabled={busy}>{busy ? "Unassigning…" : "Confirm unassign"}</button></div></Dialog>}</>;
}

export function AdminApplications() {
  const { token } = useAuth(), [apps, setApps] = useState(), [err, setErr] = useState("");
  useEffect(() => { S.applications(token).then(setApps).catch(e => setErr(e.message)); }, [token]);
  if (err) return <Err>{err}</Err>;
  if (!apps) return <Load />;
  return <><header className="admin-head"><div><p className="eyebrow">Application oversight</p><h1>All applications.</h1><p>Admin-only read access across the recruitment pipeline.</p></div></header>{apps.length ? <section className="admin-panel"><div className="admin-section-head"><div><p className="eyebrow">Application register</p><h2>{apps.length} application{apps.length === 1 ? "" : "s"}</h2></div></div><div className="admin-table admin-application-table">{apps.map(a => <Link key={a.id} to={`/admin/applications/${a.id}`}><div><b>{a.candidate.full_name}</b><small>{a.candidate.email}</small></div><div><b>{a.job.title}</b><small>{a.job.department} · {a.job.location}</small></div><Status value={a.stage} /><small>Applied {fmt(a.applied_at)}</small></Link>)}</div></section> : <div className="admin-empty"><FilePlus2 /><h3>No applications yet</h3><p>Submitted applications will appear here.</p></div>}</>;
}

function Ai({ data, onRefresh, onRetry, busy }) {
  if (!data) return <section className="admin-panel admin-ai-panel"><p>Loading authorized AI summary state…</p></section>;
  const retryable = ["failed", "unavailable"].includes(data.status);
  if (data.status !== "completed") return <section className="admin-panel admin-ai-panel"><div className="admin-section-head"><div><p className="eyebrow"><Sparkles size={14} /> AI-assisted review</p><h2>Summary not available</h2></div><button className="recruiter-icon-button" aria-label="Refresh AI summary" onClick={onRefresh} disabled={busy}><RefreshCw size={16} /></button></div><p>{data.status === "pending" ? "This AI-assisted summary is queued and preparing." : data.status === "processing" ? "This AI-assisted summary is being prepared." : "A summary is not currently available."}</p>{retryable && <button className="button" onClick={onRetry} disabled={busy}>{busy ? "Requesting retry…" : "Try again"}</button>}<p className="admin-human-notice">AI-generated assistance. Hiring decisions are made by people.</p></section>;
  return <section className="admin-panel admin-ai-panel"><div className="admin-section-head"><div><p className="eyebrow"><Sparkles size={14} /> AI-generated assistance</p><h2>Candidate summary</h2></div><button className="recruiter-icon-button" aria-label="Refresh AI summary" onClick={onRefresh} disabled={busy}><RefreshCw size={16} /></button></div><p className="admin-human-notice">AI-generated assistance. Hiring decisions are made by people.</p><h3>Profile summary</h3><ul>{data.profile_bullets?.map((x, i) => <li key={i}>{x}</li>)}</ul><div className="admin-ai-grid"><div><h3>Requirements mentioned</h3><ul>{data.requirements_found?.length ? data.requirements_found.map((x, i) => <li key={i}>{x}</li>) : <li>None listed</li>}</ul></div><div><h3>Requirements not found</h3><ul>{data.requirements_not_found?.length ? data.requirements_not_found.map((x, i) => <li key={i}>{x}</li>) : <li>None listed</li>}</ul></div></div><h3>Interview questions</h3><ol>{data.interview_questions?.map((x, i) => <li key={i}>{x}</li>)}</ol></section>;
}

export function AdminApplicationDetail() {
  const { token } = useAuth(), { applicationId } = useParams(), [detail, setDetail] = useState(), [err, setErr] = useState(""), [busy, setBusy] = useState(false), [cvBusy, setCvBusy] = useState(false);
  const load = async () => { setErr(""); try { setDetail(await S.application(token, applicationId)); } catch (e) { setErr(e.message); } };
  useEffect(() => { load(); }, [token, applicationId]);
  const retry = async () => { setBusy(true); setErr(""); try { await S.retryAiSummary(token, applicationId); await load(); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  const openCv = async () => { setCvBusy(true); setErr(""); try { const access = await S.cvAccess(token, applicationId); window.open(access.url, "_blank", "noopener,noreferrer"); } catch (e) { setErr(e.message); } finally { setCvBusy(false); } };
  if (err && !detail) return <Err>{err}</Err>;
  if (!detail) return <Load />;
  const ai = adminDetailSummary(detail);
  return <><header className="admin-head"><div><Link className="recruiter-back" to="/admin/applications">← Applications</Link><p className="eyebrow">Admin application detail</p><h1>{detail.candidate.full_name}</h1><p>{detail.candidate.email}{detail.candidate.phone ? ` · ${detail.candidate.phone}` : ""}</p></div><Status value={detail.stage} /></header>{err && <Err>{err}</Err>}<div className="admin-detail-grid"><section className="admin-panel"><p className="eyebrow">Application</p><h2>{detail.job.title}</h2><p>{detail.job.department} · {detail.job.location} · Applied {fmt(detail.applied_at)}</p><dl><div><dt>Current stage</dt><dd><Status value={detail.stage} /></dd></div><div><dt>Employment type</dt><dd>{detail.job.job_type}</dd></div><div><dt>Deadline</dt><dd>{fmt(detail.job.application_deadline)}</dd></div></dl><h3>Role context</h3><p>{detail.job.description}</p><h3>Requirements</h3><p>{detail.job.requirements}</p></section><section className="admin-panel admin-cv-panel"><div><FileText size={22} /><div><p className="eyebrow">Exact document</p><h2>Application CV snapshot</h2><p>{detail.cv.original_filename}</p></div></div><p>This opens a private, time-limited URL for the CV attached to this application.</p><button className="button" onClick={openCv} disabled={cvBusy || !detail.cv.id}>{cvBusy ? "Opening secure CV…" : "Open application CV"}</button></section><section className="admin-panel"><p className="eyebrow">Stage history</p><h2>Hiring timeline</h2>{detail.stage_history?.length ? <ol className="admin-timeline">{detail.stage_history.map((item, index) => <li key={`${item.changed_at}-${index}`}><Status value={item.stage} /><small>{fmt(item.changed_at)}</small></li>)}</ol> : <p className="admin-muted">No stage history is available.</p>}</section><section className="admin-panel"><p className="eyebrow">Interview</p><h2>Interview information</h2>{detail.interview ? <div className="admin-interview-read"><CalendarClock size={19} /><p><b>{fmtTime(detail.interview.starts_at)}</b><br />{adminInterviewLabel(detail.interview)}</p></div> : <p className="admin-muted">{adminInterviewLabel(null)}</p>}</section></div><Ai data={ai} onRefresh={load} onRetry={retry} busy={busy} /></>;
}
