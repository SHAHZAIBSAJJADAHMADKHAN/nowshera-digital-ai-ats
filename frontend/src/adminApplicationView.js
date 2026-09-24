export function adminDetailSummary(detail) {
  return detail?.ai_summary || { status: "unavailable", summary_available: false };
}

export function adminInterviewLabel(interview) {
  if (!interview) return "No interview scheduled.";
  return interview.location || interview.meeting_link || "Details provided";
}
