// Runs every case in ../fixtures/vectors.json (signed with an Ed25519 key made for that run by the
// openssl command line) against discord.mjs.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { handleEvent, handleInteraction, verify } from "./discord.mjs";

const vectors = JSON.parse(readFileSync(new URL("../fixtures/vectors.json", import.meta.url), "utf8"));
const publicKey = vectors.config.publicKey;

for (const c of vectors.cases) {
  test(c.name, () => {
    if (c.verifyOnly) {
      assert.equal(verify(c.body, c.headers, publicKey), c.expect.verified);
      return;
    }
    const run = c.mechanism === "events" ? handleEvent : handleInteraction;
    const got = run(Buffer.from(c.body, "utf8"), c.headers, { publicKey });
    assert.deepEqual(pick(got, c.expect), c.expect);
  });
}

test("refuses to run without a public key", () => {
  assert.throws(() => verify("{}", {}, undefined));
});

function pick(got, expect) {
  return Object.fromEntries(Object.keys(expect).map((k) => [k, got[k]]));
}
