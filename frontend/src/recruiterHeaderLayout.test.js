import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const css = readFileSync(resolve(here, "recruiter.css"), "utf8");

test("recruiter application header has one normal-flow desktop layout", () => {
  assert.equal((css.match(/\.recruiter-application-head\{/g) || []).length, 2);
  assert.match(css, /\.recruiter-application-head\{display:grid;grid-template-columns:minmax\(0,1fr\) auto;grid-template-areas:"back back" "identity stage"/);
  assert.match(css, /\.recruiter-application-head>div\{grid-area:identity;display:flex;align-items:flex-start;gap:14px;min-width:0\}/);
  assert.match(css, /\.recruiter-application-head>div>div\{display:grid;gap:6px;min-width:0\}/);
  assert.doesNotMatch(css, /\.recruiter-application-head\{[^}]*position:absolute/);
});

test("recruiter application header stacks identity and stage on mobile", () => {
  assert.match(css, /@media\(max-width:600px\)\{\.recruiter-application-head\{grid-template-columns:minmax\(0,1fr\);grid-template-areas:"back" "identity" "stage";row-gap:12px;margin-bottom:26px\}/);
  assert.match(css, /\.recruiter-application-head>\.recruiter-stage\{justify-self:start\}/);
});
