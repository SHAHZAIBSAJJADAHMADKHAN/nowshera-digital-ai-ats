import { api } from "../api/client";

export const adminService = {
  dashboard: token => api("/admin/dashboard/jobs", { token }),
  recruiters: (token, limit = 100, offset = 0) => api(`/admin/recruiters?limit=${limit}&offset=${offset}`, { token }),
  inviteRecruiter: (token, body) => api("/admin/recruiters", { token, method: "POST", body }),
  updateRecruiter: (token, id, body) => api(`/admin/recruiters/${id}`, { token, method: "PATCH", body }),
  deactivateRecruiter: (token, id) => api(`/admin/recruiters/${id}/deactivate`, { token, method: "POST" }),
  reactivateRecruiter: (token, id) => api(`/admin/recruiters/${id}/reactivate`, { token, method: "POST" }),
  jobs: token => api("/admin/jobs", { token }),
  job: (token, id) => api(`/admin/jobs/${id}`, { token }),
  createJob: (token, body) => api("/admin/jobs", { token, method: "POST", body }),
  updateJob: (token, id, body) => api(`/admin/jobs/${id}`, { token, method: "PATCH", body }),
  openJob: (token, id) => api(`/admin/jobs/${id}/open`, { token, method: "POST" }),
  closeJob: (token, id) => api(`/admin/jobs/${id}/close`, { token, method: "POST" }),
  assignedRecruiters: (token, jobId) => api(`/admin/jobs/${jobId}/recruiters`, { token }),
  assignRecruiter: (token, jobId, recruiterId) => api(`/admin/jobs/${jobId}/recruiters/${recruiterId}`, { token, method: "POST" }),
  unassignRecruiter: (token, jobId, recruiterId) => api(`/admin/jobs/${jobId}/recruiters/${recruiterId}`, { token, method: "DELETE" }),
  applications: token => api("/admin/applications", { token }),
  application: (token, applicationId) => api(`/admin/applications/${applicationId}`, { token }),
  cvAccess: (token, applicationId) => api(`/admin/applications/${applicationId}/cv/access`, { token }),
  aiSummary: (token, applicationId) => api(`/admin/applications/${applicationId}/ai-summary`, { token }),
  retryAiSummary: (token, applicationId) => api(`/admin/applications/${applicationId}/ai-summary/retry`, { token, method: "POST" }),
};
