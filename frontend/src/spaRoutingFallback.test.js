import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const config = JSON.parse(readFileSync(resolve(here, "../vercel.json"), "utf8"));
const app = readFileSync(resolve(here, "App.jsx"), "utf8");

test("Vercel serves the SPA entry point for every client-side route", () => {
  assert.deepEqual(config.rewrites, [{ source: "/(.*)", destination: "/index.html" }]);
});

test("the SPA contains public, role-protected, and detail route families", () => {
  for (const route of ["/login", "/register", "/candidate", "/candidate/applications/:applicationId", "/recruiter", "/recruiter/applications/:applicationId", "/admin", "/admin/applications/:applicationId"]) {
    assert.match(app, new RegExp(`path="${route.replace(/[.*+?^${}()|[\\]\\]/g, "\\$&")}"`));
  }
  assert.match(app, /<ProtectedRoute><RoleRoute role="candidate">/);
  assert.match(app, /<ProtectedRoute><RoleRoute role="recruiter">/);
  assert.match(app, /<ProtectedRoute><RoleRoute role="admin">/);
});
