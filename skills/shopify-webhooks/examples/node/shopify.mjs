// Verifies and reads Shopify webhooks. Framework-free: pass the raw body bytes and the headers; wire
// it into Express, Fastify or anything else as shown in the webhook-receiver-patterns skill.
// Node.js 18+, no dependencies.
//
// Shopify signs the raw body with HMAC-SHA256 and the app's client secret, base64 encoded (not hex),
// in X-Shopify-Hmac-Sha256. There is no timestamp. X-Shopify-Webhook-Id is the same on every
// delivery attempt of one webhook, X-Shopify-Event-Id is shared by all webhooks for one event:
// deduplicate on the first, or on the second to collapse subscriptions to the same event.

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

/** True when the request carries a valid Shopify signature over these exact bytes. */
export function verify(body, headers, secret) {
  if (!secret) throw new Error("The Shopify client secret is required (read it from the environment).");
  const raw = Buffer.isBuffer(body) ? body : Buffer.from(body ?? "", "utf8");
  const sig = header(headers, "X-Shopify-Hmac-Sha256");
  if (typeof sig !== "string") return false;
  const expected = crypto.createHmac("sha256", secret).update(raw).digest("base64");
  return safeEqual(sig, expected);
}

/**
 * Handles one request: verify, then parse. Returns the HTTP status to answer with and, when the
 * request is accepted, the topic (`type`), the webhook id to deduplicate on (`id`), the event id
 * (`eventId`) and the shop's domain (`shop`). Answer within five seconds: queue the work and
 * process it elsewhere.
 */
export function handle(body, headers, { secret } = {}) {
  const raw = Buffer.isBuffer(body) ? body : Buffer.from(body ?? "", "utf8");
  if (!verify(raw, headers, secret)) return { status: 401 };

  const type = header(headers, "X-Shopify-Topic");
  const id = header(headers, "X-Shopify-Webhook-Id");
  if (typeof type !== "string" || type === "" || typeof id !== "string" || id === "") return { status: 400 };
  let payload;
  try {
    payload = JSON.parse(raw.toString("utf8"));
  } catch {
    return { status: 400 };
  }
  if (payload === null || typeof payload !== "object" || Array.isArray(payload)) return { status: 400 };

  const eventId = header(headers, "X-Shopify-Event-Id");
  const shop = header(headers, "X-Shopify-Shop-Domain");
  return {
    status: 200,
    type,
    id,
    eventId: typeof eventId === "string" && eventId !== "" ? eventId : null,
    shop: typeof shop === "string" && shop !== "" ? shop : null,
  };
}
