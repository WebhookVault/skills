// Verifies and reads Lemon Squeezy webhooks. Framework-free: pass the raw body bytes and the
// headers; wire it into Express, Fastify or anything else as shown in the webhook-receiver-patterns
// skill. Node.js 18+, no dependencies.
//
// Lemon Squeezy signs the raw body with HMAC-SHA256 and the webhook's signing secret, hex encoded,
// in X-Signature. There is no timestamp and no event or delivery id. The event name is read from
// the signed body (meta.event_name); the unsigned X-Event-Name header is only cross-checked.

import crypto from "node:crypto";

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

/** True when the request carries a valid Lemon Squeezy signature over these exact bytes. */
export function verify(body, headers, secret) {
  if (!secret) throw new Error("The Lemon Squeezy signing secret is required (read it from the environment).");
  const raw = Buffer.isBuffer(body) ? body : Buffer.from(body ?? "", "utf8");
  const sig = header(headers, "X-Signature");
  if (typeof sig !== "string") return false;
  const expected = crypto.createHmac("sha256", secret).update(raw).digest("hex");
  return safeEqual(sig, expected);
}

/**
 * Handles one request: verify, then parse. Returns the HTTP status to answer with and, when the
 * request is accepted, the event name (`type`), `id` (always null: Lemon Squeezy sends no id to
 * deduplicate on: a hash of the body catches a resent request, and applying only newer state per
 * `resource` covers the rest) and `resource` ("<data.type>/<data.id>", null when either is missing).
 */
export function handle(body, headers, { secret } = {}) {
  const raw = Buffer.isBuffer(body) ? body : Buffer.from(body ?? "", "utf8");
  if (!verify(raw, headers, secret)) return { status: 401 };

  let payload;
  try {
    payload = JSON.parse(raw.toString("utf8"));
  } catch {
    return { status: 400 };
  }
  if (payload === null || typeof payload !== "object" || Array.isArray(payload)) return { status: 400 };

  const type = payload.meta?.event_name;
  if (typeof type !== "string" || type === "") return { status: 400 };
  const claimed = header(headers, "X-Event-Name");
  if (claimed !== undefined && claimed !== type) return { status: 400 };

  const { type: kind, id } = payload.data ?? {};
  const resource = typeof kind === "string" && kind !== "" && typeof id === "string" && id !== "" ? `${kind}/${id}` : null;
  return { status: 200, type, id: null, resource };
}
