import { api } from "../api/client";

export const recruiterService = {
  jobs: (token) => api("/recruiter/jobs", { token }),
  job: (token, jobId) => api(`/recruiter/jobs/${jobId}`, { token }),
  applications: (token, jobId) => api(`/recruiter/jobs/${jobId}/applications`, { token }),
  application: (token, applicationId) => api(`/recruiter/applications/${applicationId}`, { token }),
  cvAccess: (token, applicationId) => api(`/recruiter/applications/${applicationId}/cv/access`, { token }),
  notes: (token, applicationId) => api(`/recruiter/applications/${applicationId}/notes`, { token }),
  addNote: (token, applicationId, content) => api(`/recruiter/applications/${applicationId}/notes`, {
    token,
    method: "POST",
    body: { content },
  }),
  transition: (token, applicationId, stage) => api(`/recruiter/applications/${applicationId}/stage`, { token, method: "PATCH", body: { stage } }),
  hire: (token, applicationId) => api(`/recruiter/applications/${applicationId}/hire`, { token, method: "POST" }),
  scheduleInterview: (token, applicationId, body) => api(`/recruiter/applications/${applicationId}/interview`, { token, method: "POST", body }),
  aiSummary: (token, applicationId) => api(`/recruiter/applications/${applicationId}/ai-summary`, { token }),
  retryAiSummary: (token, applicationId) => api(`/recruiter/applications/${applicationId}/ai-summary/retry`, { token, method: "POST" }),
};
