import test from "node:test";
import assert from "node:assert/strict";
import { adminDetailSummary, adminInterviewLabel } from "./adminApplicationView.js";

test("uses admin application detail AI summary when present", () => {
  const summary = { status: "completed", summary_available: true };
  assert.equal(adminDetailSummary({ ai_summary: summary }), summary);
});

test("falls back to unavailable summary when detail has no AI result", () => {
  assert.deepEqual(adminDetailSummary({ ai_summary: null }), { status: "unavailable", summary_available: false });
});

test("formats persisted interview detail label from API data", () => {
  assert.equal(adminInterviewLabel({ location: "Nowshera", meeting_link: null }), "Nowshera");
  assert.equal(adminInterviewLabel(null), "No interview scheduled.");
});
