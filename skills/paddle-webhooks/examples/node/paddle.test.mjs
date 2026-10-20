// Runs every case in ../fixtures/vectors.json (made with the openssl command line) against paddle.mjs.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { handle, verify } from "./paddle.mjs";

const vectors = JSON.parse(readFileSync(new URL("../fixtures/vectors.json", import.meta.url), "utf8"));

for (const c of vectors.cases) {
  test(c.name, () => {
    if (c.verifyOnly) {
      assert.equal(verify(c.body, c.headers, c.secret, c.now, vectors.config.toleranceSeconds), c.expect.verified);
      return;
    }
    const got = handle(Buffer.from(c.body, "utf8"), c.headers, { secret: vectors.config.secret, now: c.now });
    assert.deepEqual(pick(got, c.expect), c.expect);
  });
}

test("refuses to run without a secret", () => {
  assert.throws(() => verify("{}", {}, undefined));
});

function pick(got, expect) {
  return Object.fromEntries(Object.keys(expect).map((k) => [k, got[k]]));
}
