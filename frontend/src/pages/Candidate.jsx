import { Link, NavLink, useParams } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BriefcaseBusiness,
  CalendarClock,
  CheckCircle2,
  ChevronRight,
  Clock3,
  FileText,
  LayoutDashboard,
  LogOut,
  MapPin,
  Search,
  ShieldCheck,
  UploadCloud,
  UserRound,
  XCircle,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { candidateService as S } from "../services/candidateService";
import { supabase } from "../lib/supabase";
import { hasEmailChange, profilePatchFromDraft } from "../profileEdit";

const fmt = (d) =>
  d
    ? new Date(d).toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : "—";
const fileSize = (bytes) => `${Math.round((bytes || 0) / 1024)} KB`;
const stages = ["applied", "shortlisted", "interview", "offer", "hired", "rejected", "withdrawn"];
const stage = (s) => <span className={`stage stage-${s}`}>{s || "unknown"}</span>;

function Load({ children = "Loading candidate workspace…" }) {
  return <p className="candidate-state" role="status">{children}</p>;
}

function Err({ children, tone = "danger" }) {
  return <p className={`candidate-alert candidate-alert--${tone}`} role={tone === "danger" ? "alert" : "status"}>{children}</p>;
}

function profileSaveError(error) {
  const message = error?.message || "";
  if (error?.status === 401 || error?.status === 403) return "Your session has expired. Sign in again to update your profile.";
  if (/already|exists|duplicate/i.test(message)) return "This email address is already in use.";
  if (/email|valid/i.test(message)) return "Enter a valid email address.";
  if (error?.status === 422) return "Check your full name and phone number, then try again.";
  return "We could not save your profile. Please try again.";
}

function Empty({ icon: Icon = FileText, title, children, action }) {
  return (
    <div className="candidate-empty">
      <Icon size={28} />
      <h3>{title}</h3>
      <p>{children}</p>
      {action}
    </div>
  );
}

function PageHead({ eyebrow, title, children, action }) {
  return (
    <header className="candidate-head">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        {children && <p>{children}</p>}
      </div>
      {action}
    </header>
  );
}

export function CandidateShell({ children }) {
  const { profile, signOut } = useAuth();
  const nav = [
    ["/candidate", LayoutDashboard, "Dashboard"],
    ["/candidate/jobs", BriefcaseBusiness, "Find jobs"],
    ["/candidate/applications", FileText, "Applications"],
    ["/candidate/cv", UploadCloud, "CV"],
    ["/candidate/profile", UserRound, "Profile"],
  ];

  return (
    <main className="candidate-shell">
      <aside className="candidate-sidebar">
        <Link className="candidate-brand" to="/">Nowshera <b>Digital</b></Link>
        <p className="candidate-kicker">Candidate workspace</p>
        <nav aria-label="Candidate navigation">
          {nav.map(([to, Icon, label]) => (
            <NavLink end={to === "/candidate"} to={to} key={to}>
              <Icon size={18} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="candidate-identity">
          <span className="candidate-avatar">{profile?.email?.[0]?.toUpperCase() || "C"}</span>
          <div>
            <b>{profile?.full_name || "Candidate"}</b>
            <small>{profile?.email}</small>
          </div>
          <button aria-label="Sign out" onClick={signOut}><LogOut size={17} /></button>
        </div>
      </aside>
      <section className="candidate-main">{children}</section>
    </main>
  );
}

export function CandidateDashboard() {
  const { token } = useAuth();
  const [data, setData] = useState({});
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    async function load() {
      setError("");
      try {
        const [profile, cvs, apps] = await Promise.all([S.profile(token), S.cvs(token), S.applications(token)]);
        if (alive) setData({ profile, cvs, apps });
      } catch (e) {
        if (alive) setError(e.message);
      }
    }
    load();
    return () => {
      alive = false;
    };
  }, [token]);

  if (error) return <Err>{error}</Err>;
  if (!data.profile) return <Load />;

  const apps = data.apps || [];
  const cvs = data.cvs || [];
  const latest = apps[0];
  const upcoming = apps.find((a) => a.stage === "interview");

  return (
    <>
      <PageHead eyebrow="Candidate dashboard" title={`Welcome, ${data.profile.full_name}.`}>
        Keep your CV current, find open roles, and track each application from one calm workspace.
      </PageHead>
      <div className="candidate-actions">
        <Link to="/candidate/jobs"><Search size={18} /><span>Find jobs</span><ChevronRight size={16} /></Link>
        <Link to="/candidate/cv"><UploadCloud size={18} /><span>Upload CV</span><ChevronRight size={16} /></Link>
        <Link to="/candidate/applications"><FileText size={18} /><span>View applications</span><ChevronRight size={16} /></Link>
      </div>
      <div className="candidate-metrics">
        <article><UploadCloud /><small>CV versions</small><b>{cvs.length}</b><p>{cvs[0]?.original_filename || "No CV uploaded yet"}</p></article>
        <article><BriefcaseBusiness /><small>Applications</small><b>{apps.length}</b><p>{latest ? `Latest: ${latest.job.title}` : "No applications yet"}</p></article>
        <article><CalendarClock /><small>Interview stage</small><b>{upcoming ? "Active" : "None"}</b><p>{upcoming?.job.title || "Interview details appear here when scheduled."}</p></article>
      </div>
      {latest ? (
        <section className="candidate-panel candidate-latest">
          <div>
            <p className="eyebrow">Latest application</p>
            <h2>{latest.job.title}</h2>
            <p>{latest.job.department} · Applied {fmt(latest.applied_at)}</p>
          </div>
          {stage(latest.stage)}
          <Link className="link-button" to={`/candidate/applications/${latest.id}`}>Open details</Link>
        </section>
      ) : (
        <Empty icon={BriefcaseBusiness} title="No applications yet" action={<Link className="button" to="/candidate/jobs">Find open jobs</Link>}>
          Your submitted applications will appear here with their current stage and CV snapshot.
        </Empty>
      )}
    </>
  );
}

export function CandidateProfile() {
  const { token, refreshProfile } = useAuth();
  const [profile, setProfile] = useState();
  const [err, setErr] = useState("");
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState();
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState(null);

  useEffect(() => {
    let alive = true;
    S.profile(token).then((p) => alive && setProfile(p)).catch((e) => alive && setErr(e.message));
    return () => {
      alive = false;
    };
  }, [token]);

  if (err) return <Err>{err}</Err>;
  if (!profile) return <Load />;

  const beginEditing = () => {
    setDraft({ full_name: profile.full_name, email: profile.email, phone: profile.phone || "" });
    setFeedback(null);
    setEditing(true);
  };

  const cancelEditing = () => {
    setDraft({ full_name: profile.full_name, email: profile.email, phone: profile.phone || "" });
    setFeedback(null);
    setEditing(false);
  };

  const reloadProfile = async () => {
    const nextProfile = await S.profile(token);
    setProfile(nextProfile);
    return nextProfile;
  };

  const save = async (event) => {
    event.preventDefault();
    if (saving || !draft) return;
    setSaving(true);
    setFeedback(null);

    let profileSaved = false;
    try {
      const patch = profilePatchFromDraft(profile, draft);
      if (Object.keys(patch).length) {
        await S.updateProfile(token, patch);
        profileSaved = true;
        await reloadProfile();
        await refreshProfile().catch(() => {});
      }

      if (hasEmailChange(profile, draft)) {
        const { error } = await supabase.auth.updateUser(
          { email: draft.email.trim() },
          { emailRedirectTo: `${window.location.origin}/candidate/profile` },
        );
        if (error) throw error;
        await reloadProfile().catch(() => {});
        setFeedback({ tone: "success", text: profileSaved
          ? "Your profile changes were saved. Email change requested — check your email to confirm the new address."
          : "Email change requested — check your email to confirm the new address." });
      } else if (profileSaved) {
        setFeedback({ tone: "success", text: "Your profile changes were saved." });
      } else {
        setFeedback({ tone: "success", text: "No profile changes to save." });
      }
      setEditing(false);
    } catch (error) {
      const message = profileSaveError(error);
      setFeedback({
        tone: "danger",
        text: profileSaved
          ? `Your name and phone were saved, but we could not request the email change. ${message}`
          : message,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <PageHead eyebrow="Your profile" title="Personal details">
        Keep the contact details attached to your applications current.
      </PageHead>
      <section className="candidate-panel candidate-form-panel">
        {editing ? (
          <form className="candidate-profile-form" onSubmit={save}>
            <label>Full name<input required value={draft.full_name} onChange={(event) => setDraft({ ...draft, full_name: event.target.value })} disabled={saving} /></label>
            <label>Email<input type="email" required value={draft.email} onChange={(event) => setDraft({ ...draft, email: event.target.value })} disabled={saving} /></label>
            <label>Phone<input value={draft.phone} onChange={(event) => setDraft({ ...draft, phone: event.target.value })} disabled={saving} /></label>
            <p><ShieldCheck size={16} /> Email changes require confirmation. Your current email remains visible until confirmation is complete.</p>
            <div className="candidate-profile-actions">
              <button className="button" type="submit" disabled={saving}>{saving ? "Saving…" : "Save Changes"}</button>
              <button className="link-button" type="button" onClick={cancelEditing} disabled={saving}>Cancel</button>
            </div>
          </form>
        ) : (
          <>
            <label>Full name<input value={profile.full_name || ""} readOnly /></label>
            <label>Email<input value={profile.email || ""} readOnly /></label>
            <label>Phone<input value={profile.phone || "Not provided"} readOnly /></label>
            <button className="button" type="button" onClick={beginEditing}>Edit Profile</button>
          </>
        )}
        {feedback && <Err tone={feedback.tone}>{feedback.text}</Err>}
      </section>
    </>
  );
}

export function CandidateCV() {
  const { token } = useAuth();
  const [cvs, setCvs] = useState();
  const [file, setFile] = useState();
  const [msg, setMsg] = useState("");

  const load = async () => {
    try {
      setCvs(await S.cvs(token));
    } catch (e) {
      setMsg(e.message);
    }
  };

  useEffect(() => {
    let alive = true;
    async function loadCvs() {
      try {
        const rows = await S.cvs(token);
        if (alive) setCvs(rows);
      } catch (e) {
        if (alive) setMsg(e.message);
      }
    }
    loadCvs();
    return () => {
      alive = false;
    };
  }, [token]);

  const upload = async (e) => {
    e.preventDefault();
    const form = e.currentTarget;
    if (!file) return setMsg("Choose a PDF to upload.");
    if (file.type !== "application/pdf" || file.size > 2097152) return setMsg("Choose a PDF no larger than 2 MiB.");
    setMsg("");
    try {
      await S.uploadCv(token, file);
      setMsg("CV uploaded successfully.");
      setFile(null);
      form.reset();
      await load();
    } catch (x) {
      setMsg(x.message);
    }
  };

  return (
    <>
      <PageHead eyebrow="CV management" title="Your CV versions">
        Applications keep the exact CV version used when you applied. New uploads never replace previous application snapshots.
      </PageHead>
      <section className="candidate-panel candidate-upload">
        <form onSubmit={upload}>
          <label className="candidate-file">
            <UploadCloud size={24} />
            <span>{file ? file.name : "Choose a PDF CV"}</span>
            <small>{file ? fileSize(file.size) : "PDF only · maximum 2 MiB"}</small>
            <input aria-label="PDF CV" type="file" accept="application/pdf" onChange={(e) => setFile(e.target.files?.[0])} />
          </label>
          <button className="button" disabled={!file}>Upload PDF</button>
        </form>
        {msg && <Err tone={msg.includes("successfully") ? "success" : "danger"}>{msg}</Err>}
      </section>
      {!cvs ? <Load>Loading CV versions…</Load> : cvs.length ? (
        <div className="candidate-list">
          {cvs.map((cv, index) => (
            <article className="candidate-row" key={cv.id}>
              <FileText />
              <div>
                <b>{cv.original_filename}</b>
                <p>{index === 0 ? "Most recent version" : "Previous version"} · Uploaded {fmt(cv.uploaded_at)} · {fileSize(cv.file_size_bytes)}</p>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <Empty icon={UploadCloud} title="No CV versions yet">Upload a PDF CV before applying to open jobs.</Empty>
      )}
    </>
  );
}

export function CandidateJobs() {
  const { token } = useAuth();
  const [jobs, setJobs] = useState();
  const [query, setQuery] = useState("");
  const [err, setErr] = useState("");

  useEffect(() => {
    let alive = true;
    S.jobs(token).then((rows) => alive && setJobs(rows)).catch((e) => alive && setErr(e.message));
    return () => {
      alive = false;
    };
  }, [token]);

  const shown = useMemo(() => jobs?.filter((j) => `${j.title} ${j.department} ${j.location}`.toLowerCase().includes(query.toLowerCase())) || [], [jobs, query]);

  if (err) return <Err>{err}</Err>;
  if (!jobs) return <Load>Loading open jobs…</Load>;

  return (
    <>
      <PageHead eyebrow="Open roles" title="Find your next opportunity.">
        Browse backend-authoritative open jobs and apply with a selected CV version.
      </PageHead>
      <label className="candidate-search">
        <Search size={18} />
        <input placeholder="Search roles, teams, locations" value={query} onChange={(e) => setQuery(e.target.value)} />
      </label>
      {shown.length ? (
        <div className="candidate-job-grid">
          {shown.map((job) => (
            <Link className="candidate-job-card" key={job.id} to={`/candidate/jobs/${job.id}`}>
              <div><span>{job.openings} opening{job.openings !== 1 ? "s" : ""}</span><ChevronRight size={17} /></div>
              <h2>{job.title}</h2>
              <p>{job.department}</p>
              <small><MapPin size={15} />{job.location} · {job.job_type}</small>
              <small>Deadline {fmt(job.application_deadline)}</small>
            </Link>
          ))}
        </div>
      ) : (
        <Empty icon={Search} title="No matching roles">Try another title, department, or location.</Empty>
      )}
    </>
  );
}

export function CandidateJobDetail() {
  const { token } = useAuth();
  const { jobId } = useParams();
  const [job, setJob] = useState();
  const [cvs, setCvs] = useState();
  const [cv, setCv] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    async function load() {
      setMsg("");
      try {
        const [jobRow, files] = await Promise.all([S.job(token, jobId), S.cvs(token)]);
        if (!alive) return;
        setJob(jobRow);
        setCvs(files);
        setCv(files[0]?.id || "");
      } catch (e) {
        if (alive) setMsg(e.message);
      }
    }
    load();
    return () => {
      alive = false;
    };
  }, [token, jobId]);

  const apply = async () => {
    if (!cv) return setMsg("Choose a CV version before submitting.");
    setBusy(true);
    setMsg("");
    try {
      const result = await S.apply(token, jobId, cv);
      setMsg(`Application submitted — stage: ${result.stage}.`);
    } catch (e) {
      setMsg(e.message);
    } finally {
      setBusy(false);
    }
  };

  if (msg && !job) return <Err>{msg}</Err>;
  if (!job) return <Load>Loading job detail…</Load>;

  return (
    <>
      <PageHead eyebrow="Open role" title={job.title} action={<Link className="link-button" to="/candidate/jobs">Back to jobs</Link>}>
        {job.department} · {job.location} · {job.job_type}
      </PageHead>
      <div className="candidate-detail-grid">
        <section className="candidate-panel">
          <h2>About this role</h2>
          <p>{job.description}</p>
          <h3>Requirements</h3>
          <p>{job.requirements}</p>
          <dl>
            <div><dt>Deadline</dt><dd>{fmt(job.application_deadline)}</dd></div>
            <div><dt>Openings</dt><dd>{job.openings}</dd></div>
          </dl>
        </section>
        <section className="candidate-panel candidate-apply">
          <p className="eyebrow">Application review</p>
          <h2>Submit with a CV snapshot</h2>
          {!cvs ? <Load>Loading CV versions…</Load> : !cvs.length ? (
            <Empty icon={UploadCloud} title="Upload a CV first" action={<Link className="button" to="/candidate/cv">Upload a CV</Link>}>
              You need an uploaded PDF CV before applying.
            </Empty>
          ) : (
            <>
              <label>CV version
                <select value={cv} onChange={(e) => setCv(e.target.value)}>
                  {cvs.map((f) => <option value={f.id} key={f.id}>{f.original_filename} · {fmt(f.uploaded_at)}</option>)}
                </select>
              </label>
              <p className="candidate-disclosure"><ShieldCheck size={16} /> This exact CV version is permanently attached to the application. AI may assist recruiters with factual summaries, but people make all hiring decisions.</p>
              <button className="button" disabled={busy || !cv} onClick={apply}>{busy ? "Submitting…" : "Submit application"}</button>
            </>
          )}
          {msg && <Err tone={msg.includes("submitted") ? "success" : "danger"}>{msg}</Err>}
        </section>
      </div>
    </>
  );
}

export function CandidateApplications() {
  const { token } = useAuth();
  const [apps, setApps] = useState();
  const [err, setErr] = useState("");

  useEffect(() => {
    let alive = true;
    S.applications(token).then((rows) => alive && setApps(rows)).catch((e) => alive && setErr(e.message));
    return () => {
      alive = false;
    };
  }, [token]);

  if (err) return <Err>{err}</Err>;
  if (!apps) return <Load>Loading applications…</Load>;

  return (
    <>
      <PageHead eyebrow="My applications" title="Track your progress.">
        Review stage history, interview details, and the exact CV snapshot used for each application.
      </PageHead>
      {apps.length ? (
        <div className="candidate-list">
          {apps.map((app) => (
            <Link className="candidate-application-card" key={app.id} to={`/candidate/applications/${app.id}`}>
              <div>
                <h2>{app.job.title}</h2>
                <p>{app.job.department} · Applied {fmt(app.applied_at)}</p>
              </div>
              {stage(app.stage)}
              <ChevronRight size={18} />
            </Link>
          ))}
        </div>
      ) : (
        <Empty icon={BriefcaseBusiness} title="No applications yet" action={<Link className="button" to="/candidate/jobs">Find jobs</Link>}>
          Submitted applications will appear here with their current stage.
        </Empty>
      )}
    </>
  );
}

export function CandidateApplicationDetail() {
  const { token } = useAuth();
  const { applicationId } = useParams();
  const [application, setApplication] = useState();
  const [err, setErr] = useState("");
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      setApplication(await S.application(token, applicationId));
    } catch (e) {
      setErr(e.message);
    }
  };

  useEffect(() => {
    let alive = true;
    async function loadApplication() {
      setErr("");
      try {
        const row = await S.application(token, applicationId);
        if (alive) setApplication(row);
      } catch (e) {
        if (alive) setErr(e.message);
      }
    }
    loadApplication();
    return () => {
      alive = false;
    };
  }, [token, applicationId]);

  const withdraw = async () => {
    setBusy(true);
    setErr("");
    try {
      await S.withdraw(token, applicationId);
      setConfirm(false);
      await load();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  if (err && !application) return <Err>{err}</Err>;
  if (!application) return <Load>Loading application detail…</Load>;

  const canWithdraw = ["applied", "shortlisted", "interview", "offer"].includes(application.stage);
  const terminal = ["hired", "rejected", "withdrawn"].includes(application.stage);

  return (
    <>
      <PageHead eyebrow="Application detail" title={application.job.title} action={<Link className="link-button" to="/candidate/applications">Back to applications</Link>}>
        {application.job.department} · Applied {fmt(application.applied_at)}
      </PageHead>
      {err && <Err>{err}</Err>}
      <div className="candidate-detail-grid">
        <section className="candidate-panel">
          <div className="candidate-stage-head">
            <div>
              <p className="eyebrow">Current stage</p>
              <h2>{stage(application.stage)}</h2>
            </div>
            {terminal ? <XCircle /> : <Clock3 />}
          </div>
          <p><b>CV used for this application:</b> {application.cv?.original_filename || "Unavailable"}</p>
          {application.stage === "withdrawn" && <p className="candidate-disclosure">This application remains linked to its original CV. If this job is still open, you may reapply with a new CV from the job page.</p>}
          {canWithdraw && <button className="candidate-danger" onClick={() => setConfirm(true)}>Withdraw application</button>}
        </section>
        <section className="candidate-panel">
          <h2>Timeline</h2>
          {application.stage_history?.length ? (
            <ol className="candidate-timeline">
              {application.stage_history.map((item, index) => (
                <li key={`${item.changed_at}-${index}`}>
                  <span />
                  <div>{stage(item.stage)}<small>{fmt(item.changed_at)}</small></div>
                </li>
              ))}
            </ol>
          ) : (
            <p className="candidate-muted">No stage history is available.</p>
          )}
        </section>
        <section className="candidate-panel">
          <h2>Interview</h2>
          {application.interview ? (
            <article className="candidate-interview">
              <CalendarClock size={20} />
              <div>
                <b>{fmt(application.interview.starts_at)}</b>
                <p>{application.interview.meeting_link ? <a href={application.interview.meeting_link}>Join meeting</a> : application.interview.location || "Details to follow"}</p>
              </div>
            </article>
          ) : (
            <p className="candidate-muted">No interview scheduled.</p>
          )}
        </section>
      </div>
      {confirm && (
        <div className="modal candidate-modal" role="dialog" aria-modal="true" aria-labelledby="withdraw-title">
          <div>
            <AlertTriangle size={26} />
            <h2 id="withdraw-title">Withdraw this application?</h2>
            <p>This is terminal for this application. Recruiters can no longer move it through the pipeline. You may submit a new application later if the job is still open.</p>
            <div className="candidate-modal-actions">
              <button className="link-button" onClick={() => setConfirm(false)} disabled={busy}>Cancel</button>
              <button className="candidate-danger" disabled={busy} onClick={withdraw}>{busy ? "Withdrawing…" : "Confirm withdraw"}</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
