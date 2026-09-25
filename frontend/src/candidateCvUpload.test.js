import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(resolve(here, "pages/Candidate.jsx"), "utf8");

test("successful CV upload captures the form before async work, resets it safely, and reloads the list", () => {
  assert.match(source, /e\.preventDefault\(\);\s*const form = e\.currentTarget;/);
  assert.match(source, /await S\.uploadCv\(token, file\);\s*setMsg\("CV uploaded successfully\."\);\s*setFile\(null\);\s*form\.reset\(\);\s*await load\(\);/);
  assert.doesNotMatch(source, /e\.currentTarget\.reset\(\)/);
  assert.match(source, /setCvs\(await S\.cvs\(token\)\);/);
});

test("CV upload keeps PDF and 2 MiB validation", () => {
  assert.match(source, /file\.type !== "application\/pdf" \|\| file\.size > 2097152/);
  assert.match(source, /Choose a PDF no larger than 2 MiB\./);
});

test("CV upload failures show the upload error without success", () => {
  assert.match(source, /catch \(x\) \{\s*setMsg\(x\.message\);\s*\}/);
  assert.match(source, /setMsg\(""\);\s*try \{\s*await S\.uploadCv/);
});
