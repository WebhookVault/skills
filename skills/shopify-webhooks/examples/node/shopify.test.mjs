// Runs every case in ../fixtures/vectors.json (made with the openssl command line) against shopify.mjs.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { handle, verify } from "./shopify.mjs";

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

test("returns the event id and shop domain", () => {
  const c = vectors.cases.find((x) => x.name === "orders/create");
  const got = handle(Buffer.from(c.body, "utf8"), c.headers, { secret: vectors.config.secret });
  assert.equal(got.eventId, c.headers["X-Shopify-Event-Id"]);
  assert.equal(got.shop, c.headers["X-Shopify-Shop-Domain"]);
});

function pick(got, expect) {
  return Object.fromEntries(Object.keys(expect).map((k) => [k, got[k]]));
}
