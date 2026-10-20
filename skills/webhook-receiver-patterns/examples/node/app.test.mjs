// Drives the receiver over real HTTP. Signatures are made with the openssl command line, not with
// the code under test, so verify() is checked against an independent implementation.

import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createApp, MAX_BODY_BYTES } from "./app.mjs";

const SECRET = "test-receiver-secret";
const NOW = 1760000000;
const queued = [];
let failNextEnqueue = false;
let server;
let base;

before(async () => {
  const app = createApp({
    secret: SECRET,
    now: () => NOW,
    enqueue: async (event) => {
      if (failNextEnqueue) { failNextEnqueue = false; throw new Error("queue down"); }
      queued.push(event.id);
    },
  });
  await new Promise((resolve) => { server = app.listen(0, resolve); });
  base = `http://127.0.0.1:${server.address().port}`;
});
after(() => server.close());

/** HMAC-SHA256 by openssl over "<t>.<body>", hex. */
function opensslSign(t, body) {
  const out = execFileSync("openssl", ["dgst", "-sha256", "-hmac", SECRET, "-hex"], { input: Buffer.concat([Buffer.from(`${t}.`), Buffer.from(body)]) });
  return out.toString().trim().split(/\s+/).pop();
}

function post(body, { t = NOW, signature, headers = {} } = {}) {
  const sig = signature ?? `t=${t},v1=${opensslSign(t, body)}`;
  return fetch(`${base}/webhooks`, { method: "POST", body, headers: { "Content-Type": "application/json", "Webhook-Signature": sig, ...headers } });
}

test("a signed event is acknowledged and queued once", async () => {
  const res = await post('{"id":"evt_test_a","type":"order.created"}');
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), { received: true });
  assert.equal(queued.filter((id) => id === "evt_test_a").length, 1);
});

test("the same event again is acknowledged and not queued twice", async () => {
  await post('{"id":"evt_test_b"}');
  const res = await post('{"id":"evt_test_b"}');
  assert.equal(res.status, 200);
  assert.equal((await res.json()).duplicate, true);
  assert.equal(queued.filter((id) => id === "evt_test_b").length, 1);
});

test("a wrong signature is refused with 401 and nothing is queued", async () => {
  const before = queued.length;
  const res = await post('{"id":"evt_test_c"}', { signature: `t=${NOW},v1=${"0".repeat(64)}` });
  assert.equal(res.status, 401);
  assert.equal(queued.length, before);
});

test("an unverified request does not use up the event id", async () => {
  await post('{"id":"evt_test_d"}', { signature: "t=1,v1=bad" });
  const res = await post('{"id":"evt_test_d"}');
  assert.equal(res.status, 200);
  assert.equal(queued.filter((id) => id === "evt_test_d").length, 1);
});

test("a stale timestamp is refused even with a valid signature", async () => {
  const res = await post('{"id":"evt_test_e"}', { t: NOW - 3600 });
  assert.equal(res.status, 401);
});

test("a missing signature header is refused", async () => {
  const res = await fetch(`${base}/webhooks`, { method: "POST", body: '{"id":"evt_test_f"}', headers: { "Content-Type": "application/json" } });
  assert.equal(res.status, 401);
});

test("a signed body that is not JSON is refused with 400 after verifying", async () => {
  const res = await post("not json");
  assert.equal(res.status, 400);
  assert.equal((await res.json()).error, "invalid_json");
});

test("a signed event without an id is refused with 400", async () => {
  const res = await post('{"type":"order.created"}');
  assert.equal(res.status, 400);
});

test("a body over the limit is refused with 413", async () => {
  const big = JSON.stringify({ id: "evt_test_big", pad: "x".repeat(MAX_BODY_BYTES) });
  const res = await post(big);
  assert.equal(res.status, 413);
});

test("a failed hand-off answers 500 so the sender retries", async () => {
  failNextEnqueue = true;
  const res = await post('{"id":"evt_test_g"}');
  assert.equal(res.status, 500);
});

test("the signature covers the exact bytes: reformatted JSON is refused", async () => {
  const body = '{"id":"evt_test_h"}';
  const sig = `t=${NOW},v1=${opensslSign(NOW, body)}`;
  const res = await post('{ "id": "evt_test_h" }', { signature: sig });
  assert.equal(res.status, 401);
});
