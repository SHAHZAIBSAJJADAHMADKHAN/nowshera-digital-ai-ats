import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve, dirname } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(resolve(here, "context/AuthContext.jsx"), "utf8");

test("auth state callback defers profile resolution outside the Supabase callback tick", () => {
  assert.match(source, /setTimeout\(\(\)=>\{timer\.current=null;resolve\(s\)\.catch\(\(\)=>\{\}\)\},0\)/);
  assert.match(source, /onAuthStateChange\(\(_,s\)=>\{deferResolve\(s\)\}\)/);
});

test("login starts profile resolution without blocking the sign-in result", () => {
  assert.match(source, /signIn:async\(email,password\)=>\{const result=await supabase\.auth\.signInWithPassword/);
  assert.doesNotMatch(source, /await resolve\(result\.data\.session\)/);
  assert.match(source, /deferResolve\(result\.data\.session\).*return result/);
});

test("same-user refresh keeps the resolved profile while it revalidates", () => {
  assert.match(source, /const sameUser=isSameResolvedUser\(resolvedUserId\.current,s\);/);
  assert.match(source, /if\(!sameUser\)\{resolvedUserId\.current=null;setLoading\(true\);setProfile\(null\)\}/);
});
