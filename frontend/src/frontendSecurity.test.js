import test from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";

const root = fileURLToPath(new URL("./", import.meta.url));

function files(dir) {
  return readdirSync(dir).flatMap(name => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? files(path) : [path];
  });
}

test("frontend source does not call Gemini or expose server-only AI secrets", () => {
  const source = files(root).filter(path => /\.(js|jsx|css)$/.test(path) && !path.endsWith("frontendSecurity.test.js")).map(path => readFileSync(path, "utf8")).join("\n").toLowerCase();
  for (const forbidden of ["gemini", "generativelanguage", "googleapis", "gemini_api_key", "api_secret", "service_role", "supabase_secret_key"]) {
    assert.equal(source.includes(forbidden), false, forbidden);
  }
});
