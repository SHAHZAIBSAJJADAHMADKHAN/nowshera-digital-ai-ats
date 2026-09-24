export function getRecruiterInterviewForDisplay(application, scheduled) {
  return application?.interview || scheduled || null;
}
