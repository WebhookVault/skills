// Verifies and reads GitHub webhook deliveries. Framework-free: pass the raw body bytes and the
// headers; wire it into Express, Fastify or anything else as shown in the webhook-receiver-patterns
// skill. Node.js 18+, no dependencies.
//
// GitHub signs the raw body with HMAC-SHA256 and the webhook's secret, hex encoded and prefixed
// "sha256=", in X-Hub-Signature-256. The older SHA-1 X-Hub-Signature header is never accepted.
// There is no timestamp, so a replayed delivery verifies: deduplicate on X-GitHub-Delivery.
// Set the webhook's content type to application/json (a form-encoded delivery is not read here).

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

/** True when the request carries a valid GitHub SHA-256 signature over these exact bytes. */
export function verify(body, headers, secret) {
  if (!secret) throw new Error("The GitHub webhook secret is required (read it from the environment).");
  const raw = Buffer.isBuffer(body) ? body : Buffer.from(body ?? "", "utf8");
  const sig = header(headers, "X-Hub-Signature-256");
  if (typeof sig !== "string") return false;
  const expected = "sha256=" + crypto.createHmac("sha256", secret).update(raw).digest("hex");
  return safeEqual(sig, expected);
}

/**
 * Handles one request: verify, then parse. Returns the HTTP status to answer with and, when the
 * request is accepted, the event name (`type`, from X-GitHub-Event), the `action` in the body (null
 * when it has none) and the delivery id to deduplicate on (`id`, from X-GitHub-Delivery). Answer
 * within ten seconds: queue the work and process it elsewhere.
 */
export function handle(body, headers, { secret } = {}) {
  const raw = Buffer.isBuffer(body) ? body : Buffer.from(body ?? "", "utf8");
  if (!verify(raw, headers, secret)) return { status: 401 };

  const type = header(headers, "X-GitHub-Event");
  if (typeof type !== "string" || type === "") return { status: 400 };
  let payload;
  try {
    payload = JSON.parse(raw.toString("utf8"));
  } catch {
    return { status: 400 };
  }
  if (payload === null || typeof payload !== "object" || Array.isArray(payload)) return { status: 400 };

  const delivery = header(headers, "X-GitHub-Delivery");
  return {
    status: 200,
    type,
    action: typeof payload.action === "string" ? payload.action : null,
    id: typeof delivery === "string" && delivery !== "" ? delivery : null,
  };
}
