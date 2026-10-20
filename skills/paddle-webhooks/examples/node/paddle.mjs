// Verifies and reads Paddle Billing notifications. Framework-free: pass the raw body bytes and the
// headers; wire it into Express, Fastify or anything else as shown in the webhook-receiver-patterns
// skill. Node.js 18+, no dependencies.
//
// Paddle sends "Paddle-Signature: ts=<unix seconds>;h1=<hex>" (several h1 values while a secret is
// being rotated). Each h1 is HMAC-SHA256, keyed with the notification destination's secret key string,
// over "<ts>:<raw body>". Paddle's guidance is to reject a timestamp more than five seconds from
// local time, which is tight: keep the server clock synchronised.

import crypto from "node:crypto";

export const TOLERANCE_SECONDS = 5;

function header(headers, name) {
  const key = Object.keys(headers ?? {}).find((k) => k.toLowerCase() === name.toLowerCase());
  const value = key === undefined ? undefined : headers[key];
  return Array.isArray(value) ? value[0] : value;
}

function safeEqual(a, b) {
  const x = Buffer.from(a, "utf8");
  const y = Buffer.from(b, "utf8");
  return x.length === y.length && crypto.timingSafeEqual(x, y);
}

/** True when the request carries a valid, fresh Paddle signature over these exact bytes. */
export function verify(body, headers, secret, now = Math.floor(Date.now() / 1000), tolerance = TOLERANCE_SECONDS) {
  if (!secret) throw new Error("The Paddle notification secret key is required (read it from the environment).");
  const raw = Buffer.isBuffer(body) ? body : Buffer.from(body ?? "", "utf8");
  const value = header(headers, "Paddle-Signature");
  if (typeof value !== "string") return false;

  const timestamps = [];
  const signatures = [];
  for (const part of value.split(";")) {
    const at = part.indexOf("=");
    if (at < 0) continue;
    const k = part.slice(0, at).trim();
    const v = part.slice(at + 1).trim();
    if (k === "ts") timestamps.push(v);
    else if (k === "h1") signatures.push(v);
  }
  if (timestamps.length !== 1 || !/^\d{1,12}$/.test(timestamps[0]) || signatures.length === 0) return false;
  const ts = timestamps[0];
  if (Math.abs(now - Number(ts)) > tolerance) return false;

  const expected = crypto.createHmac("sha256", secret).update(`${ts}:`).update(raw).digest("hex");
  // Check every candidate (no early exit on the first match) so timing does not reveal which matched.
  let ok = false;
  for (const s of signatures) ok = safeEqual(s.toLowerCase(), expected) || ok;
  return ok;
}

/**
 * Handles one request: verify, then parse. Returns the HTTP status to answer with and, when the
 * request is accepted, the event name (`type`, Paddle's event_type) and the id to deduplicate on
 * (`id`, Paddle's event_id). Answer 200 quickly and process elsewhere: Paddle retries on anything else.
 */
export function handle(body, headers, { secret, now } = {}) {
  const raw = Buffer.isBuffer(body) ? body : Buffer.from(body ?? "", "utf8");
  if (!verify(raw, headers, secret, now)) return { status: 401 };

  let payload;
  try {
    payload = JSON.parse(raw.toString("utf8"));
  } catch {
    return { status: 400 };
  }
  if (payload === null || typeof payload !== "object") return { status: 400 };
  if (typeof payload.event_type !== "string" || typeof payload.event_id !== "string") return { status: 400 };
  return { status: 200, type: payload.event_type, id: payload.event_id };
}
