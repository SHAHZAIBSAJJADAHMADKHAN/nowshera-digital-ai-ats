import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { hasEmailChange, profilePatchFromDraft } from "./profileEdit.js";

const here = dirname(fileURLToPath(import.meta.url));
const page = readFileSync(resolve(here, "pages/Candidate.jsx"), "utf8");

const profile = { full_name: "Candidate One", email: "candidate@example.com", phone: "+923001234567" };

test("profile edits patch only changed name and phone, never email", () => {
  assert.deepEqual(profilePatchFromDraft(profile, { full_name: " Candidate Two ", email: "new@example.com", phone: " " }), {
    full_name: "Candidate Two", phone: null,
  });
});

test("profile draft preserves pending email separately from persisted email", () => {
  assert.equal(hasEmailChange(profile, { full_name: profile.full_name, email: "NEW@example.com", phone: profile.phone }), true);
  assert.equal(hasEmailChange(profile, { full_name: profile.full_name, email: "candidate@example.com", phone: profile.phone }), false);
});

test("candidate profile UI uses authenticated Supabase email update with the profile callback URL", () => {
  assert.match(page, /supabase\.auth\.updateUser\(/);
  assert.match(page, /emailRedirectTo: `\$\{window\.location\.origin\}\/candidate\/profile`/);
  assert.match(page, /Email change requested — check your email to confirm the new address\./);
  assert.doesNotMatch(page, /updateProfile\(token,\s*\{[^}]*email/);
});

test("candidate profile UI provides edit, cancel, and protected-field-free persistence", () => {
  assert.match(page, />Edit Profile</);
  assert.match(page, /"Save Changes"/);
  assert.match(page, />Cancel</);
  assert.match(page, /profilePatchFromDraft\(profile, draft\)/);
  const helper = readFileSync(resolve(here, "profileEdit.js"), "utf8");
  assert.doesNotMatch(helper, /user_id|is_active|role|email\s*:/);
});
