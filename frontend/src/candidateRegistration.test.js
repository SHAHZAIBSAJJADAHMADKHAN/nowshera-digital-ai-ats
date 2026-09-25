import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(resolve(here, "pages/Public.jsx"), "utf8");

test("candidate registration signs out the immediate signup session and redirects to login", () => {
  assert.match(source, /if\(register\)\{if\(r\.data\.session\)await a\.signOut\(\);nav\("\/login",\{replace:true,state:\{message:"Account created successfully\. Please sign in\."\}\}\);return\}/);
  assert.match(source, /useState\(location\.state\?\.message\?\?""\)/);
});

test("candidate registration no longer presents an email-confirmation instruction", () => {
  assert.doesNotMatch(source, /Check your email to confirm your account/);
  assert.match(source, /Account created successfully\. Please sign in\./);
});

test("normal login and recruiter password setup remain separate from candidate registration", () => {
  assert.match(source, /await a\.signIn\(f\.email,f\.password\)/);
  assert.match(source, /export function SetPassword\(\)/);
  assert.match(source, /Recruiter invitation/);
  assert.doesNotMatch(source, /inviteUserByEmail|\/auth\/v1\/invite/);
});
