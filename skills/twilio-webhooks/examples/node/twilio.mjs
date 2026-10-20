// Verifies and reads Twilio webhook requests (form-encoded and JSON). Framework-free: pass the raw
// body, the headers and the public URL Twilio called; wire it into Express, Fastify or anything else
// as shown in the webhook-receiver-patterns skill. Node.js 18+, no dependencies.
//
// Twilio signs with HMAC-SHA1 and the account auth token, base64 encoded, in X-Twilio-Signature.
// Form bodies: the full URL followed by every POST parameter name and value, sorted by name.
// JSON bodies: the URL carries bodySHA256 (hex SHA-256 of the raw body) and nothing is appended.
// The URL must be the one Twilio called, exactly: scheme, host, port, path, query and encoding.

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

const isJson = (headers) => String(header(headers, "Content-Type") ?? "").toLowerCase().startsWith("application/json");

/** The form fields as Twilio sent them, in order ("+" is a space, then percent-decoding). */
export function formFields(raw) {
  return [...new URLSearchParams(raw.toString("utf8")).entries()];
}

/** True when X-Twilio-Signature matches this URL and body. */
export function verify(body, headers, url, authToken) {
  if (!authToken) throw new Error("The Twilio auth token is required (read it from the environment).");
  const raw = Buffer.isBuffer(body) ? body : Buffer.from(body ?? "", "utf8");
  const signature = header(headers, "X-Twilio-Signature");
  if (typeof signature !== "string" || typeof url !== "string") return false;

  let signed = url;
  if (isJson(headers)) {
    let claimed;
    try { claimed = new URL(url).searchParams.get("bodySHA256"); } catch { return false; }
    if (!claimed) return false;
    const actual = crypto.createHash("sha256").update(raw).digest("hex");
    if (!safeEqual(claimed.toLowerCase(), actual)) return false;
  } else {
    // Sorted by name in code-unit order (Twilio: "Unix-style case-sensitive"); a stable sort keeps
    // repeated names in the order they arrived.
    const fields = formFields(raw).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
    for (const [name, value] of fields) signed += name + value;
  }
  const expected = crypto.createHmac("sha1", authToken).update(signed, "utf8").digest("base64");
  return safeEqual(signature, expected);
}

/**
 * Handles one request: verify, then read. Returns the status to answer with and, when accepted,
 * the status value Twilio reported (`type`) and the resource SID (`id`). Twilio has no event id;
 * a retry carries I-Twilio-Idempotency-Token, which is the better key when present.
 */
export function handle(body, headers, url, { authToken } = {}) {
  const raw = Buffer.isBuffer(body) ? body : Buffer.from(body ?? "", "utf8");
  if (!verify(raw, headers, url, authToken)) return { status: 401 };

  let fields;
  if (isJson(headers)) {
    try { fields = JSON.parse(raw.toString("utf8")); } catch { return { status: 400 }; }
    if (fields === null || typeof fields !== "object" || Array.isArray(fields)) return { status: 400 };
  } else {
    fields = Object.fromEntries(formFields(raw));
  }
  const pick = (...names) => names.map((n) => fields[n]).find((v) => typeof v === "string" && v.length > 0) ?? null;
  return {
    status: 200,
    type: pick("MessageStatus", "SmsStatus", "CallStatus"),
    id: pick("MessageSid", "SmsSid", "CallSid"),
    idempotencyToken: header(headers, "I-Twilio-Idempotency-Token") ?? null,
  };
}
