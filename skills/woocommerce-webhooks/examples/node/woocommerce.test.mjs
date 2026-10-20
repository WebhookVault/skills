// Runs every case in ../fixtures/vectors.json (made with the openssl command line) against woocommerce.mjs.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { handle, verify } from "./woocommerce.mjs";

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

test("a ping-shaped body with a trailing newline is not a ping", () => {
  assert.equal(handle(Buffer.from("webhook_id=12\n"), {}, { secret: vectors.config.secret }).status, 401);
});

function pick(got, expect) {
  return Object.fromEntries(Object.keys(expect).map((k) => [k, got[k]]));
}
