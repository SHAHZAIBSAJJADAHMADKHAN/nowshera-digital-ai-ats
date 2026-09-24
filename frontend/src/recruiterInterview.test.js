import test from "node:test";
import assert from "node:assert/strict";
import { getRecruiterInterviewForDisplay } from "./recruiterInterview.js";

test("uses persisted recruiter-detail interview from the API on initial load", () => {
  const interview = {
    id: "33333333-3333-3333-3333-333333333333",
    starts_at: "2026-09-25T10:00:00Z",
    ends_at: "2026-09-25T11:00:00Z",
    location: "Nowshera",
    meeting_link: null,
  };

  assert.equal(getRecruiterInterviewForDisplay({ interview }, null), interview);
});

test("falls back to the newly scheduled in-session interview until detail reload catches up", () => {
  const scheduled = {
    id: "33333333-3333-3333-3333-333333333333",
    starts_at: "2026-09-25T10:00:00Z",
    location: "Nowshera",
  };

  assert.equal(getRecruiterInterviewForDisplay({ interview: null }, scheduled), scheduled);
});

test("returns null when no persisted or newly scheduled interview exists", () => {
  assert.equal(getRecruiterInterviewForDisplay({ interview: null }, null), null);
});
