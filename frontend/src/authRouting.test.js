import test from "node:test";
import assert from "node:assert/strict";
import { protectedRouteState, roleRouteState } from "./authRouting.js";

test("role guard waits while session exists but the new role profile is still loading", () => {
  assert.deepEqual(roleRouteState({ loading: true, session: { access_token: "new" }, profile: null }, "candidate"), { type: "loading" });
  assert.deepEqual(roleRouteState({ loading: false, session: { access_token: "new" }, profile: null }, "candidate"), { type: "loading" });
});

test("role guard allows matching roles after profile synchronization", () => {
  assert.deepEqual(roleRouteState({ loading: false, session: { access_token: "new" }, profile: { role: "candidate" } }, "candidate"), { type: "allow" });
});

test("role guard still blocks real unauthorized role access", () => {
  assert.deepEqual(roleRouteState({ loading: false, session: { access_token: "admin" }, profile: { role: "admin" } }, "candidate"), { type: "redirect", to: "/admin" });
});

test("role guard handles account switching without access-denied while profile is being replaced", () => {
  assert.deepEqual(roleRouteState({ loading: true, session: { access_token: "candidate" }, profile: null }, "candidate"), { type: "loading" });
  assert.deepEqual(roleRouteState({ loading: false, session: { access_token: "candidate" }, profile: { role: "candidate" } }, "candidate"), { type: "allow" });
});

test("logout makes the protected workspace inaccessible", () => {
  assert.deepEqual(protectedRouteState({ loading: false, session: null }), { type: "redirect", to: "/login" });
});
