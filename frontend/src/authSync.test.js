import test from "node:test";
import assert from "node:assert/strict";
import { isSameResolvedUser } from "./authSync.js";

for (const role of ["candidate", "recruiter", "admin"]) {
  test(`${role} keeps its resolved workspace during a same-user session refresh`, () => {
    assert.equal(isSameResolvedUser(`${role}-id`, { user: { id: `${role}-id` }, access_token: "refreshed" }), true);
  });
}

test("a different user requires fresh identity resolution", () => {
  assert.equal(isSameResolvedUser("admin-id", { user: { id: "candidate-id" } }), false);
});

test("a missing session cannot retain an authenticated profile", () => {
  assert.equal(isSameResolvedUser("admin-id", null), false);
});
