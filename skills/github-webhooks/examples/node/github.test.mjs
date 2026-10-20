// Runs every case in ../fixtures/vectors.json (made with the openssl command line, plus GitHub's own
// published example) against github.mjs.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { handle, verify } from "./github.mjs";

const vectors = JSON.parse(readFileSync(new URL("../fixtures/vectors.json", import.meta.url), "utf8"));

for (const c of vectors.cases) {
  test(c.name, () => {
    if (c.verifyOnly) {
      assert.equal(verify(c.body, c.headers, c.secret), c.expect.verified);
      return;
    }
    const got = handle(Buffer.from(c.body, "utf8"), c.headers, { secret: vectors.config.secret });
    assert.deepEqual(pick(got, c.expect), c.expect);
  });
}

test("refuses to run without a secret", () => {
  assert.throws(() => verify("{}", {}, undefined));
});

function pick(got, expect) {
  return Object.fromEntries(Object.keys(expect).map((k) => [k, got[k]]));
}
