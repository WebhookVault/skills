// Verifies and reads SendGrid Event Webhook requests (signed event webhook). Framework-free: pass the
// raw body and the headers; wire it into Express, Fastify or anything else as shown in the
// webhook-receiver-patterns skill. Node.js 18+, no dependencies.
//
// SendGrid signs the timestamp header value followed by the raw body with ECDSA and SHA-256, and
// sends the base64 signature in X-Twilio-Email-Event-Webhook-Signature. The verification key is the
// base64 public key shown in the Event Webhook settings. The body is a JSON array of events.

import crypto from "node:crypto";

function header(headers, name) {
  const key = Object.keys(headers ?? {}).find((k) => k.toLowerCase() === name.toLowerCase());
  const value = key === undefined ? undefined : headers[key];
  return Array.isArray(value) ? value[0] : value;
}

/** Loads the base64 key from the SendGrid settings (DER SubjectPublicKeyInfo). Do this once. */
export function loadPublicKey(base64Key) {
  if (!base64Key) throw new Error("The SendGrid verification key is required (read it from the environment).");
  return crypto.createPublicKey({ key: Buffer.from(base64Key, "base64"), format: "der", type: "spki" });
}

/** True when the signature over timestamp + raw body verifies with this key. */
export function verify(body, headers, publicKey) {
  const raw = Buffer.isBuffer(body) ? body : Buffer.from(body ?? "", "utf8");
  const signature = header(headers, "X-Twilio-Email-Event-Webhook-Signature");
  const timestamp = header(headers, "X-Twilio-Email-Event-Webhook-Timestamp");
  if (typeof signature !== "string" || typeof timestamp !== "string" || !/^[A-Za-z0-9+/]+={0,2}$/.test(signature)) return false;
  const signed = Buffer.concat([Buffer.from(timestamp, "utf8"), raw]);
  try {
    return crypto.verify("sha256", signed, publicKey, Buffer.from(signature, "base64"));
  } catch {
    return false; // a signature that is not a valid DER sequence
  }
}

/**
 * Handles one request: verify, then parse the batch. Returns the status to answer with and, when
 * accepted, each event's name and sg_event_id (the id SendGrid says to deduplicate on).
 *
 * No timestamp window is applied: SendGrid states none and retries a failed batch for up to 24
 * hours, so an age limit could refuse its own retries. Deduplicating on sg_event_id covers replays.
 */
export function handle(body, headers, { publicKey } = {}) {
  const raw = Buffer.isBuffer(body) ? body : Buffer.from(body ?? "", "utf8");
  if (!verify(raw, headers, publicKey)) return { status: 401 };
  let batch;
  try { batch = JSON.parse(raw.toString("utf8")); } catch { return { status: 400 }; }
  if (!Array.isArray(batch) || batch.some((e) => e === null || typeof e !== "object" || Array.isArray(e))) return { status: 400 };
  return {
    status: 200,
    events: batch.map((e) => ({
      type: typeof e.event === "string" ? e.event : null,
      id: typeof e.sg_event_id === "string" ? e.sg_event_id : null,
    })),
  };
}
