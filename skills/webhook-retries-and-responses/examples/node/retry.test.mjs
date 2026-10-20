import { test } from "node:test";
import assert from "node:assert/strict";
import { isRetryableStatus, backoffDelay, parseRetryAfter, deliverWithRetries } from "./retry.mjs";

test("only statuses that can succeed later are retried", () => {
  for (const s of [408, 425, 429, 500, 502, 503, 504, 599]) assert.equal(isRetryableStatus(s), true, String(s));
  for (const s of [200, 301, 400, 401, 403, 404, 409, 410, 413, 422]) assert.equal(isRetryableStatus(s), false, String(s));
});

test("backoff doubles under the cap and full jitter spans zero to the ceiling", () => {
  const top = () => 0.999999;
  assert.equal(backoffDelay(0, { baseMs: 1000, random: top }), 999);
  assert.equal(backoffDelay(3, { baseMs: 1000, random: top }), 7999);
  assert.equal(backoffDelay(30, { baseMs: 1000, capMs: 60_000, random: top }), 59_999);
  assert.equal(backoffDelay(5, { baseMs: 1000, random: () => 0 }), 0);
  assert.throws(() => backoffDelay(-1));
});

test("Retry-After reads delay-seconds and the RFC 9110 HTTP-date, and nothing else", () => {
  const now = Date.parse("Wed, 21 Oct 2015 07:27:00 GMT");
  assert.equal(parseRetryAfter("120", now), 120_000);
  assert.equal(parseRetryAfter(" 0 ", now), 0);
  assert.equal(parseRetryAfter("Wed, 21 Oct 2015 07:28:00 GMT", now), 60_000);
  assert.equal(parseRetryAfter("Wed, 21 Oct 2015 07:26:00 GMT", now), 0);
  assert.equal(parseRetryAfter("-5", now), null);
  assert.equal(parseRetryAfter("1.5", now), null);
  assert.equal(parseRetryAfter("tomorrow", now), null);
  assert.equal(parseRetryAfter(undefined, now), null);
});

/** A fake receiver answering a scripted sequence; "throw" stands for a network error. */
function script(...answers) {
  let i = 0;
  return async () => {
    const a = answers[Math.min(i++, answers.length - 1)];
    if (a === "throw") throw new Error("connection reset");
    return typeof a === "number" ? { status: a, headers: {} } : a;
  };
}

function clock() {
  let t = 0;
  const waits = [];
  return { now: () => t, sleep: async (ms) => { waits.push(ms); t += ms; }, waits };
}

test("a receiver that recovers is delivered after retries", async () => {
  const c = clock();
  const r = await deliverWithRetries(script(503, "throw", 200), { random: () => 0.5, ...c });
  assert.deepEqual(r, { outcome: "delivered", attempts: 3, status: 200 });
  assert.deepEqual(c.waits, [500, 1000]);
});

test("a permanent answer stops at once", async () => {
  const c = clock();
  const r = await deliverWithRetries(script(400), c);
  assert.deepEqual(r, { outcome: "rejected", attempts: 1, status: 400 });
  assert.deepEqual(c.waits, []);
});

test("Retry-After from a 429 is honoured instead of the backoff", async () => {
  const c = clock();
  const r = await deliverWithRetries(script({ status: 429, headers: { "retry-after": "7" } }, 200), { random: () => 0.5, ...c });
  assert.equal(r.outcome, "delivered");
  assert.deepEqual(c.waits, [7000]);
});

test("the attempt budget ends in a dead letter", async () => {
  const c = clock();
  const r = await deliverWithRetries(script(500), { maxAttempts: 4, random: () => 0, ...c });
  assert.deepEqual(r, { outcome: "dead_letter", attempts: 4, status: 500 });
  assert.equal(c.waits.length, 3);
});

test("the time budget ends the attempts early rather than waiting past it", async () => {
  const c = clock();
  const r = await deliverWithRetries(script({ status: 503, headers: { "retry-after": "7200" } }), { maxElapsedMs: 3_600_000, ...c });
  assert.deepEqual(r, { outcome: "dead_letter", attempts: 1, status: 503 });
  assert.deepEqual(c.waits, []);
});
