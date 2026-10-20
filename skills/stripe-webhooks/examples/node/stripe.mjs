// Verifies and reads Stripe webhook events. Framework-free: pass the raw body bytes and the headers;
// wire it into Express, Fastify or anything else as shown in the webhook-receiver-patterns skill.
// Node.js 18+, no dependencies.
//
// Stripe sends "Stripe-Signature: t=<timestamp>,v1=<hex>[,v1=<hex>...][,v0=<hex>]". Each v1 is
// HMAC-SHA256 over "<t>.<raw body>" with the endpoint's signing secret (the whole "whsec_..." string
// is the key). While a secret is being rolled there are two v1 values: any one may match. v0 is for
// test mode and is never accepted. Stripe's libraries refuse timestamps more than five minutes old.

import crypto from "node:crypto";

export const TOLERANCE_SECONDS = 300;

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

/** True when the request carries a valid, fresh Stripe signature over these exact bytes. */
export function verify(body, headers, secret, now = Math.floor(Date.now() / 1000), tolerance = TOLERANCE_SECONDS) {
  if (!secret) throw new Error("The Stripe endpoint signing secret is required (read it from the environment).");
  const raw = Buffer.isBuffer(body) ? body : Buffer.from(body ?? "", "utf8");
  const value = header(headers, "Stripe-Signature");
  if (typeof value !== "string") return false;

  const timestamps = [];
  const candidates = [];
  for (const part of value.split(",")) {
    const eq = part.indexOf("=");
    if (eq < 0) continue;
    const key = part.slice(0, eq);
    const val = part.slice(eq + 1);
    if (key === "t") timestamps.push(val);
    else if (key === "v1") candidates.push(val); // v0 and unknown keys are ignored
  }
  if (timestamps.length !== 1 || !/^\d{1,12}$/.test(timestamps[0]) || candidates.length === 0) return false;
  const ts = timestamps[0];
  if (Math.abs(now - Number(ts)) > tolerance) return false;

  const expected = crypto.createHmac("sha256", secret).update(`${ts}.`).update(raw).digest("hex");
  // Check every candidate (no early exit) so the time taken does not say which one matched.
  let ok = false;
  for (const candidate of candidates) ok = safeEqual(candidate, expected) || ok;
  return ok;
}

/**
 * Handles one request: verify, then parse. Returns the HTTP status to answer with and, when the
 * request is accepted, the event name (`type`) and the event id to deduplicate on (`id`). Answer
 * 2xx quickly: queue the work and process it elsewhere.
 */
export function handle(body, headers, { secret, now, tolerance } = {}) {
  const raw = Buffer.isBuffer(body) ? body : Buffer.from(body ?? "", "utf8");
  if (!verify(raw, headers, secret, now, tolerance)) return { status: 401 };

  let event;
  try {
    event = JSON.parse(raw.toString("utf8"));
  } catch {
    return { status: 400 };
  }
  if (event === null || typeof event !== "object" || Array.isArray(event)) return { status: 400 };
  if (typeof event.id !== "string" || typeof event.type !== "string") return { status: 400 };
  return { status: 200, type: event.type, id: event.id };
}
