// Verifies and reads Slack Events API and interactivity requests. Framework-free: pass the raw body
// bytes and the headers; wire it into Express, Fastify or anything else as shown in the
// webhook-receiver-patterns skill. Node.js 18+, no dependencies.
//
// Slack signs "v0:<X-Slack-Request-Timestamp>:<raw body>" with HMAC-SHA256 and the app's signing
// secret, hex encoded and prefixed "v0=", in X-Slack-Signature. Slack's own example rejects a
// timestamp more than five minutes from local time.

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

/** True when the request carries a valid, fresh Slack signature over these exact bytes. */
export function verify(body, headers, secret, now = Math.floor(Date.now() / 1000), tolerance = TOLERANCE_SECONDS) {
  if (!secret) throw new Error("The Slack signing secret is required (read it from the environment).");
  const raw = Buffer.isBuffer(body) ? body : Buffer.from(body ?? "", "utf8");
  const ts = header(headers, "X-Slack-Request-Timestamp");
  const sig = header(headers, "X-Slack-Signature");
  if (typeof ts !== "string" || !/^\d{1,12}$/.test(ts) || typeof sig !== "string") return false;
  if (Math.abs(now - Number(ts)) > tolerance) return false;
  const expected = "v0=" + crypto.createHmac("sha256", secret).update(`v0:${ts}:`).update(raw).digest("hex");
  return safeEqual(sig, expected);
}

/**
 * Handles one request: verify, then parse. Returns the HTTP status to answer with and, when the
 * request is accepted, the event name (`type`), the id to deduplicate on (`id`, Slack's event_id;
 * null for interactions, which have none) and, for url_verification, the text to reply with.
 * Answer within three seconds: queue the work and process it elsewhere.
 */
export function handle(body, headers, { secret, now } = {}) {
  const raw = Buffer.isBuffer(body) ? body : Buffer.from(body ?? "", "utf8");
  if (!verify(raw, headers, secret, now)) return { status: 401 };

  const contentType = String(header(headers, "Content-Type") ?? "").toLowerCase();
  let payload;
  try {
    if (contentType.startsWith("application/x-www-form-urlencoded")) {
      // Interactivity: one form field, "payload", holding JSON.
      const field = new URLSearchParams(raw.toString("utf8")).get("payload");
      if (field === null) return { status: 400 };
      payload = JSON.parse(field);
    } else {
      payload = JSON.parse(raw.toString("utf8"));
    }
  } catch {
    return { status: 400 };
  }
  if (payload === null || typeof payload !== "object") return { status: 400 };

  if (payload.type === "url_verification") {
    // Answered only after the signature checked out, so nobody else can register this URL.
    if (typeof payload.challenge !== "string") return { status: 400 };
    return { status: 200, type: "url_verification", id: null, reply: payload.challenge };
  }
  if (payload.type === "event_callback") {
    const type = payload.event?.type;
    if (typeof type !== "string" || typeof payload.event_id !== "string") return { status: 400 };
    return { status: 200, type, id: payload.event_id };
  }
  if (typeof payload.type !== "string") return { status: 400 };
  return { status: 200, type: payload.type, id: null };
}
