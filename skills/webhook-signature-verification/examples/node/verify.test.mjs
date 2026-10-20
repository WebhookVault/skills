// Every vector in ../fixtures/vectors.json was signed by the openssl command line (make_vectors.py),
// so these tests check this code against an independent implementation. Each vector is also
// mutated into the failure cases a verifier must reject.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  verifyHmacBody, verifyTimestampHeader, verifyVersionedTimestamp, verifyStandardWebhooks,
  verifyUrlForm, verifyEd25519, verifyEcdsaP256, verifySharedToken, isFresh, safeEqual,
} from "./verify.mjs";

const vectors = JSON.parse(readFileSync(new URL("../fixtures/vectors.json", import.meta.url), "utf8"));
const raw = (v) => Buffer.from(v.body, "utf8");
const tamper = (v) => Buffer.concat([raw(v), Buffer.from(" ")]);
const STALE = (v) => v.now + 10_000;

// One entry per family: how to verify, and how to build each failure case from a good vector.
const families = {
  "hmac-body": {
    ok: (v, o = {}) => verifyHmacBody({ body: raw(v), signature: v.signature, secret: v.secret, encoding: v.encoding, prefix: v.prefix, ...o }),
    wrongSecret: { secret: "test-wrong-secret" },
  },
  "hmac-timestamp-header": {
    ok: (v, o = {}) => verifyTimestampHeader({ body: raw(v), header: v.header, secret: v.secret, now: v.now, tolerance: v.tolerance,
      pairSeparator: v.pairSeparator, timestampKey: v.timestampKey, signatureKey: v.signatureKey, joiner: v.joiner, ...o }),
    wrongSecret: { secret: "test-wrong-secret" },
    stale: true,
  },
  "hmac-versioned-timestamp": {
    ok: (v, o = {}) => verifyVersionedTimestamp({ body: raw(v), timestamp: v.timestamp, signature: v.signature, secret: v.secret, now: v.now, tolerance: v.tolerance, ...o }),
    wrongSecret: { secret: "test-wrong-secret" },
    stale: true,
  },
  "standard-webhooks": {
    ok: (v, o = {}) => verifyStandardWebhooks({ body: raw(v), id: v.id, timestamp: v.timestamp, signature: v.signature, secret: v.secret, now: v.now, tolerance: v.tolerance, ...o }),
    wrongSecret: { secret: "whsec_" + Buffer.alloc(32, 7).toString("base64") },
    stale: true,
  },
  "hmac-url-form": {
    ok: (v, o = {}) => verifyUrlForm({ url: v.url, params: v.params, signature: v.signature, secret: v.secret, ...o }),
    wrongSecret: { secret: "test-wrong-token" },
  },
  "ed25519": {
    ok: (v, o = {}) => verifyEd25519({ body: raw(v), timestamp: v.timestamp, signature: v.signature, publicKey: v.publicKey, now: v.now, tolerance: v.tolerance, ...o }),
    stale: true,
  },
  "ecdsa-p256": {
    ok: (v, o = {}) => verifyEcdsaP256({ body: raw(v), timestamp: v.timestamp, signature: v.signature, publicKey: v.publicKey, now: v.now, tolerance: v.tolerance, ...o }),
    stale: true,
  },
  "shared-token": {
    ok: (v, o = {}) => verifySharedToken({ value: v.signature, token: v.secret, ...o }),
    wrongSecret: { token: "test-other-token" },
  },
};

for (const v of vectors) {
  const f = families[v.family];
  test(`${v.family} ${v.name}: the signature from openssl verifies`, () => {
    assert.ok(f, `no test mapping for family ${v.family}`);
    assert.equal(f.ok(v), true);
  });

  if (v.body !== undefined) {
    test(`${v.family} ${v.name}: one changed byte in the body is rejected`, () => {
      assert.equal(f.ok(v, { body: tamper(v) }), false);
    });
    test(`${v.family} ${v.name}: the body parsed and re-serialised is rejected unless identical`, () => {
      if (!v.body.startsWith("{")) return;
      const reserialised = JSON.stringify(JSON.parse(v.body), null, 2);
      if (reserialised === v.body) return;
      assert.equal(f.ok(v, { body: reserialised }), false);
    });
  }
  if (f.wrongSecret) {
    test(`${v.family} ${v.name}: the wrong secret is rejected`, () => {
      assert.equal(f.ok(v, f.wrongSecret), false);
    });
  }
  if (f.stale) {
    test(`${v.family} ${v.name}: a timestamp outside the tolerance is rejected`, () => {
      assert.equal(f.ok(v, { now: STALE(v) }), false);
    });
  }
  test(`${v.family} ${v.name}: a missing signature is rejected without throwing`, () => {
    const missing = v.family === "hmac-timestamp-header" ? { header: undefined }
      : v.family === "shared-token" ? { value: undefined } : { signature: undefined };
    assert.equal(f.ok(v, missing), false);
  });
  test(`${v.family} ${v.name}: a garbage signature is rejected without throwing`, () => {
    const garbage = v.family === "hmac-timestamp-header" ? { header: "nonsense;;==,," }
      : v.family === "shared-token" ? { value: "x" } : { signature: "%%%not-a-signature%%%" };
    assert.equal(f.ok(v, garbage), false);
  });
}

// The providers' own published examples (GitHub and Slack documentation, the Standard Webhooks
// library tests), copied exactly with their source and read date.
const published = JSON.parse(readFileSync(new URL("../fixtures/published.json", import.meta.url), "utf8"));
for (const v of published) {
  test(`published ${v.name}: verifies as the provider documents`, () => {
    assert.equal(families[v.family].ok(v), true);
  });
  test(`published ${v.name}: one changed byte is rejected`, () => {
    assert.equal(families[v.family].ok(v, { body: tamper(v) }), false);
  });
}

test("a URL-bound signature fails when the URL is rebuilt behind a proxy", () => {
  const v = vectors.find((x) => x.family === "hmac-url-form");
  assert.equal(verifyUrlForm({ url: v.url.replace("https://", "http://"), params: v.params, signature: v.signature, secret: v.secret }), false);
});

test("a timestamp header with two timestamps is rejected", () => {
  const v = vectors.find((x) => x.family === "hmac-timestamp-header" && x.name === "comma-json");
  assert.equal(verifyTimestampHeader({ body: raw(v), header: `t=1,${v.header}`, secret: v.secret, now: v.now }), false);
});

test("freshness accepts whole seconds within the tolerance only", () => {
  assert.equal(isFresh("1000", 1200, 300), true);
  assert.equal(isFresh("1000", 1301, 300), false);
  assert.equal(isFresh("1000", 699, 300), false);
  assert.equal(isFresh("1000.5", 1000, 300), false);
  assert.equal(isFresh("", 1000, 300), false);
  assert.equal(isFresh(undefined, 1000, 300), false);
});

test("safeEqual is false for different lengths and missing values", () => {
  assert.equal(safeEqual("abc", "abcd"), false);
  assert.equal(safeEqual(undefined, "a"), false);
  assert.equal(safeEqual("a", "a"), true);
});
