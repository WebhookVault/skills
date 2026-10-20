// Verifies and reads Resend webhooks. Framework-free: pass the raw body bytes and the headers; wire it
// into Express, Fastify or anything else as shown in the webhook-receiver-patterns skill.
// Node.js 18+, no dependencies.
//
// Resend delivers through Svix, which follows the Standard Webhooks scheme. The signing key is the
// base64 text after "whsec_" in the signing secret. The signed string is
// "<svix-id>.<svix-timestamp>.<raw body>"; HMAC-SHA256 with the decoded key, base64 encoded, goes in
// svix-signature as space-separated "v1,<signature>" entries (several while a secret is rotated).
// Svix's libraries reject a timestamp more than five minutes from local time.

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

function signingKey(secret) {
  const encoded = secret.startsWith("whsec_") ? secret.slice("whsec_".length) : secret;
  const key = Buffer.from(encoded, "base64");
  if (key.length === 0) throw new Error("The Resend signing secret is not valid base64 after the whsec_ prefix.");
  return key;
}

/** True when the request carries a valid, fresh Resend signature over these exact bytes. */
export function verify(body, headers, secret, now = Math.floor(Date.now() / 1000), tolerance = TOLERANCE_SECONDS) {
  if (!secret) throw new Error("The Resend signing secret is required (read it from the environment).");
  const key = signingKey(secret);
  const raw = Buffer.isBuffer(body) ? body : Buffer.from(body ?? "", "utf8");
  const id = header(headers, "svix-id");
  const ts = header(headers, "svix-timestamp");
  const sigs = header(headers, "svix-signature");
  if (typeof id !== "string" || id === "" || typeof sigs !== "string") return false;
  if (typeof ts !== "string" || !/^\d{1,12}$/.test(ts)) return false;
  if (Math.abs(now - Number(ts)) > tolerance) return false;

  const expected = crypto.createHmac("sha256", key).update(`${id}.${ts}.`).update(raw).digest("base64");
  // Only v1 entries count; other versions are ignored. Check every candidate, no early exit.
  let ok = false;
  for (const entry of sigs.split(/\s+/)) {
    const comma = entry.indexOf(",");
    if (comma < 0 || entry.slice(0, comma) !== "v1") continue;
    ok = safeEqual(entry.slice(comma + 1), expected) || ok;
  }
  return ok;
}

/**
 * Handles one request: verify, then parse. Returns the HTTP status to answer with and, when the
 * request is accepted, the event name (`type`) and the id to deduplicate on (`id`, the svix-id
 * header, which stays the same across retries). Answer 2xx quickly and process elsewhere.
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
  if (payload === null || typeof payload !== "object" || typeof payload.type !== "string") return { status: 400 };
  return { status: 200, type: payload.type, id: header(headers, "svix-id") };
}
