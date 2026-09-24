import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const page = readFileSync(resolve(here, "pages/Admin.jsx"), "utf8");
const service = readFileSync(resolve(here, "services/adminService.js"), "utf8");

test("active and inactive recruiters expose the correct lifecycle actions", () => {
  assert.match(page, /r\.is_active\?<button className="admin-action danger"[\s\S]*?>Deactivate<\/button>:<button className="admin-action open"[\s\S]*?>Reactivate<\/button>/);
  assert.match(page, /onClick=\{\(\)=>setEditing\(r\)\}/);
});

test("recruiter edit form pre-fills only safe editable fields", () => {
  assert.match(page, /useState\(\{full_name:recruiter\.full_name,phone:recruiter\.phone\|\|""\}\)/);
  assert.match(page, /<label>Email<input value=\{recruiter\.email\} readOnly aria-readonly="true"\/>/);
  assert.match(page, /S\.updateRecruiter\(token,recruiter\.id,\{full_name:f\.full_name\.trim\(\),phone:f\.phone\.trim\(\)\|\|null\}\)/);
});

test("reactivation requires confirmation and refreshes the recruiter list", () => {
  assert.match(page, /title=\{dialog\.kind==="reactivate"\?"Reactivate recruiter\?"/);
  assert.match(page, /S\.reactivateRecruiter\(token,dialog\.recruiter\.id\)/);
  assert.match(page, /await load\(\)/);
  assert.match(page, /disabled=\{busy\}/);
});

test("admin recruiter service uses dedicated edit and reactivation endpoints", () => {
  assert.match(service, /updateRecruiter: \(token, id, body\) => api\(`\/admin\/recruiters\/\$\{id\}`, \{ token, method: "PATCH", body \}\)/);
  assert.match(service, /reactivateRecruiter: \(token, id\) => api\(`\/admin\/recruiters\/\$\{id\}\/reactivate`, \{ token, method: "POST" \}\)/);
});
