// Retrying a webhook delivery (or any call to a receiver) safely: exponential backoff with full
// jitter under a cap, retry only what can succeed later, honour Retry-After, give up after a budget
// and park the delivery as a dead letter. No dependencies.
//
// Randomness, the clock and sleep are parameters so the behaviour is testable exactly.

/** Statuses worth retrying: the receiver may succeed later. Every other 4xx is a permanent answer. */
export function isRetryableStatus(status) {
  return status === 408 || status === 425 || status === 429 || (status >= 500 && status <= 599);
}

/**
 * Full jitter: a random delay between 0 and min(cap, base * 2^attempt), in milliseconds.
 * `attempt` counts from 0 for the first retry. `random` returns [0, 1).
 */
export function backoffDelay(attempt, { baseMs = 1000, capMs = 15 * 60 * 1000, random = Math.random } = {}) {
  if (!Number.isInteger(attempt) || attempt < 0) throw new RangeError("attempt is a whole number from 0");
  const ceiling = Math.min(capMs, baseMs * 2 ** Math.min(attempt, 30));
  return Math.floor(random() * ceiling);
}

/**
 * Retry-After (RFC 9110 10.2.3) as milliseconds to wait: either delay-seconds ("120") or an
 * HTTP-date ("Wed, 21 Oct 2015 07:28:00 GMT"). Null when absent or unreadable; never negative.
 */
export function parseRetryAfter(value, nowMs = Date.now()) {
  if (typeof value !== "string") return null;
  const v = value.trim();
  if (/^\d+$/.test(v)) return Number(v) * 1000;
  if (!/^[A-Za-z]{3}, \d{2} [A-Za-z]{3} \d{4} \d{2}:\d{2}:\d{2} GMT$/.test(v)) return null;
  const at = Date.parse(v);
  return Number.isNaN(at) ? null : Math.max(0, at - nowMs);
}

/**
 * Sends with retries. `send()` resolves to { status, headers } or rejects on a network error or
 * timeout (both retryable). Returns { outcome: "delivered" | "rejected" | "dead_letter", attempts,
 * status }. The total wait never exceeds `maxElapsedMs`; a Retry-After longer than what is left
 * ends the attempts rather than being ignored.
 */
export async function deliverWithRetries(send, {
  maxAttempts = 8, baseMs = 1000, capMs = 15 * 60 * 1000, maxElapsedMs = 60 * 60 * 1000,
  random = Math.random, sleep = (ms) => new Promise((r) => setTimeout(r, ms)), now = Date.now,
} = {}) {
  const started = now();
  let last = { status: null };
  let made = 0;
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    made = attempt;
    let retryAfterMs = null;
    try {
      const res = await send();
      last = res;
      if (res.status >= 200 && res.status <= 299) return { outcome: "delivered", attempts: attempt, status: res.status };
      if (!isRetryableStatus(res.status)) return { outcome: "rejected", attempts: attempt, status: res.status };
      retryAfterMs = parseRetryAfter(res.headers?.["retry-after"], now());
    } catch {
      last = { status: null };
    }
    if (attempt === maxAttempts) break;
    const wait = retryAfterMs ?? backoffDelay(attempt - 1, { baseMs, capMs, random });
    if (now() - started + wait > maxElapsedMs) break;
    await sleep(wait);
  }
  return { outcome: "dead_letter", attempts: made, status: last.status };
}
