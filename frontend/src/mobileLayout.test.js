import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));

for (const [role, file, shell] of [
  ["candidate", "candidate.css", "candidate-shell"],
  ["recruiter", "recruiter.css", "recruiter-shell"],
  ["admin", "admin.css", "admin-shell"],
]) {
  test(`${role} workspace collapses its desktop shell for tablet and mobile`, () => {
    const css = readFileSync(resolve(here, file), "utf8");
    assert.match(css, new RegExp(`@media\\(max-width:900px\\)\\{\\s*\\.${shell}\\{grid-template-columns:1fr\\}`));
    assert.match(css, /@media\(max-width:600px\)/);
  });
}
