// Verifies and reads WooCommerce webhooks. Framework-free: pass the raw body bytes and the headers;
// wire it into Express, Fastify or anything else as shown in the webhook-receiver-patterns skill.
// Node.js 18+, no dependencies.
//
// WooCommerce signs the raw body with HMAC-SHA256 and the webhook's secret, base64 encoded, in
// X-WC-Webhook-Signature. There is no timestamp. When a webhook is saved WooCommerce sends one
// unsigned ping whose body is exactly "webhook_id=<number>"; that single shape is acknowledged and
// nothing else unsigned is.

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

/** True when the request carries a valid WooCommerce signature over these exact bytes. */
export function verify(body, headers, secret) {
  if (!secret) throw new Error("The WooCommerce webhook secret is required (read it from the environment).");
  const raw = Buffer.isBuffer(body) ? body : Buffer.from(body ?? "", "utf8");
  const sig = header(headers, "X-WC-Webhook-Signature");
  if (typeof sig !== "string") return false;
  const expected = crypto.createHmac("sha256", secret).update(raw).digest("base64");
  return safeEqual(sig, expected);
}

/**
 * Handles one request: verify, then parse. Returns the HTTP status to answer with and, when the
 * request is accepted, the topic (`type`, for example "order.created") and the delivery id to
 * deduplicate on (`id`, null when WooCommerce sent none). The activation ping answers 200 with
 * type "ping" and id null. Answer quickly: queue the work and process it elsewhere.
 */
export function handle(body, headers, { secret } = {}) {
  const raw = Buffer.isBuffer(body) ? body : Buffer.from(body ?? "", "utf8");

  // Only a request with no signature header at all AND exactly this body is the ping.
  if (header(headers, "X-WC-Webhook-Signature") === undefined && /^webhook_id=[0-9]+$/.test(raw.toString("latin1"))) {
    if (!secret) throw new Error("The WooCommerce webhook secret is required (read it from the environment).");
    return { status: 200, type: "ping", id: null };
  }
  if (!verify(raw, headers, secret)) return { status: 401 };

  const type = header(headers, "X-WC-Webhook-Topic");
  if (typeof type !== "string" || type === "") return { status: 400 };
  let payload;
  try {
    payload = JSON.parse(raw.toString("utf8"));
  } catch {
    return { status: 400 };
  }
  if (payload === null || typeof payload !== "object" || Array.isArray(payload)) return { status: 400 };

  const delivery = header(headers, "X-WC-Webhook-Delivery-ID");
  return { status: 200, type, id: typeof delivery === "string" && delivery !== "" ? delivery : null };
}
