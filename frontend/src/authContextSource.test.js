import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve, dirname } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(resolve(here, "context/AuthContext.jsx"), "utf8");

test("auth state callback defers profile resolution outside the Supabase callback tick", () => {
  assert.match(source, /setTimeout\(\(\) => \{\s*timer\.current = null;\s*resolve\(s\)\.catch\(\(\) => \{\}\);\s*\}, 0\)/);
  assert.match(source, /onAuthStateChange\(\(_, s\) => \{\s*deferResolve\(s\);\s*\}\)/);
});

test("login starts profile resolution without blocking the sign-in result", () => {
  assert.match(source, /signIn: async \(email, password\) => \{\s*const result = await supabase\.auth\.signInWithPassword/);
  assert.doesNotMatch(source, /await resolve\(result\.data\.session\)/);
  assert.match(source, /deferResolve\(result\.data\.session\);\s*\}\s*return result;/);
});

test("same-user refresh keeps the resolved profile while it revalidates", () => {
  assert.match(source, /const sameUser = isSameResolvedUser\(resolvedUserId\.current, s\);/);
  assert.match(source, /if \(!sameUser\) \{\s*resolvedUserId\.current = null;\s*setLoading\(true\);\s*setProfile\(null\);/);
});

test("a missing ATS profile bootstraps only after authenticated profile resolution is denied", () => {
  assert.match(source, /if \(error\.status !== 403\) throw error;/);
  assert.match(source, /api\("\/candidate\/profile\/bootstrap", \{ token: s\.access_token, method: "POST" \}\)/);
  assert.match(source, /nextProfile = await api\("\/auth\/me", \{ token: s\.access_token \}\);/);
});
