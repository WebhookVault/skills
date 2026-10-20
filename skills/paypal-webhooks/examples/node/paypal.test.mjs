// Runs every case in ../fixtures/vectors.json (made with the openssl command line) against paypal.mjs.
// fetchCertificate answers from the vectors' certificates and throws for any URL not listed there, so
// a request that reaches the network for a URL the rule should have refused fails the test.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { crc32, handle, isTrustedCertificateUrl, verify } from "./paypal.mjs";

const vectors = JSON.parse(readFileSync(new URL("../fixtures/vectors.json", import.meta.url), "utf8"));

const options = {
  webhookId: vectors.config.webhookId,
  fetchCertificate: async (url) => {
    const pem = vectors.config.certificates[url];
    if (pem === undefined) throw new Error(`no certificate for ${url}`);
    return pem;
  },
};

for (const c of vectors.cases) {
  test(c.name, async () => {
    if (c.verifyOnly) {
      assert.equal(await verify(c.body, c.headers, options), c.expect.verified);
      return;
    }
    const got = await handle(Buffer.from(c.body, "utf8"), c.headers, options);
    assert.deepEqual(pick(got, c.expect), c.expect);
  });
}

test("refuses to run without a webhook id", async () => {
  await assert.rejects(verify("{}", {}, { fetchCertificate: options.fetchCertificate }));
});

test("refuses to run without a certificate fetcher", async () => {
  await assert.rejects(handle("{}", {}, { webhookId: "x" }));
});

test("crc32 matches the standard check value", () => {
  assert.equal(crc32(Buffer.from("123456789")), 0xcbf43926);
  assert.equal(crc32(Buffer.alloc(0)), 0);
});

test("certificate URL rule", () => {
  assert.equal(isTrustedCertificateUrl("https://api.paypal.com/v1/notifications/certs/C"), true);
  assert.equal(isTrustedCertificateUrl("https://paypal.com/c"), true);
  assert.equal(isTrustedCertificateUrl("https://evilpaypal.com/c"), false);
  assert.equal(isTrustedCertificateUrl("https://paypal.com@evil.test/c"), false);
  assert.equal(isTrustedCertificateUrl("https://user:pw@api.paypal.com/c"), false);
  assert.equal(isTrustedCertificateUrl("https://api.paypal.com:8443/c"), false);
  assert.equal(isTrustedCertificateUrl("http://api.paypal.com/c"), false);
  assert.equal(isTrustedCertificateUrl("not a url"), false);
});

function pick(got, expect) {
  return Object.fromEntries(Object.keys(expect).map((k) => [k, got[k]]));
}
