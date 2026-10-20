// Runs every case in ../fixtures/vectors.json (made with the openssl command line, plus Twilio's own
// published example) against twilio.mjs.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { handle, verify } from "./twilio.mjs";

const vectors = JSON.parse(readFileSync(new URL("../fixtures/vectors.json", import.meta.url), "utf8"));

for (const c of vectors.cases) {
  test(c.name, () => {
    if (c.verifyOnly) {
      assert.equal(verify(c.body, c.headers, c.url, c.secret), c.expect.verified);
      return;
    }
    const got = handle(Buffer.from(c.body, "utf8"), c.headers, c.url, { authToken: vectors.config.secret });
    assert.deepEqual(Object.fromEntries(Object.keys(c.expect).map((k) => [k, got[k]])), c.expect);
  });
}

test("refuses to run without an auth token", () => {
  assert.throws(() => verify("", {}, "https://example.test/", ""));
});

test("passes on the idempotency token of a retry", () => {
  const c = vectors.cases.find((x) => x.headers["I-Twilio-Idempotency-Token"]);
  const got = handle(Buffer.from(c.body, "utf8"), c.headers, c.url, { authToken: vectors.config.secret });
  assert.equal(got.idempotencyToken, c.headers["I-Twilio-Idempotency-Token"]);
});
