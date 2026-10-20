// Runs every case in ../fixtures/vectors.json (signed by the openssl command line with a P-256 key
// made for that run) against sendgrid.mjs.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { handle, loadPublicKey } from "./sendgrid.mjs";

const vectors = JSON.parse(readFileSync(new URL("../fixtures/vectors.json", import.meta.url), "utf8"));
const publicKey = loadPublicKey(vectors.config.publicKey);

for (const c of vectors.cases) {
  test(c.name, () => {
    const got = handle(Buffer.from(c.body, "utf8"), c.headers, { publicKey });
    assert.deepEqual(Object.fromEntries(Object.keys(c.expect).map((k) => [k, got[k]])), c.expect);
  });
}

test("refuses to run without a key", () => {
  assert.throws(() => loadPublicKey(""));
});
