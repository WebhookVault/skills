// Verifies and reads Discord Webhook Events and Interactions endpoint requests. Framework-free: pass the
// raw body bytes and the headers; wire it into Express, Fastify or anything else as shown in the
// webhook-receiver-patterns skill. Node.js 18+, no dependencies.
//
// Both use the same signature: Ed25519 over "<X-Signature-Timestamp><raw body>", hex encoded in
// X-Signature-Ed25519, checked with the application's public key (64 hex characters, from the
// developer portal). Discord sends no tolerance guidance for it and neither does this code: the
// timestamp is part of the signed message, nothing more. Discord also sends requests with a bad
// signature on purpose when you save the endpoint URL and expects 401 for them.
//
// handleEvent is for Webhook Events (answer 204); handleInteraction is for the Interactions endpoint
// (answer 200 with a JSON body). Use the one that matches the URL you registered.

import crypto from "node:crypto";

const HEX_SIGNATURE = /^[0-9a-fA-F]{128}$/;
const HEX_KEY = /^[0-9a-fA-F]{64}$/;

function header(headers, name) {
  const key = Object.keys(headers ?? {}).find((k) => k.toLowerCase() === name.toLowerCase());
  const value = key === undefined ? undefined : headers[key];
  return Array.isArray(value) ? value[0] : value;
}

/** True when the request carries a valid Discord Ed25519 signature over these exact bytes. */
export function verify(body, headers, publicKey) {
  if (!publicKey) throw new Error("The Discord application public key is required (read it from the environment).");
  const raw = Buffer.isBuffer(body) ? body : Buffer.from(body ?? "", "utf8");
  const ts = header(headers, "X-Signature-Timestamp");
  const sig = header(headers, "X-Signature-Ed25519");
  if (typeof ts !== "string" || ts === "" || typeof sig !== "string") return false;
  if (!HEX_SIGNATURE.test(sig) || !HEX_KEY.test(publicKey)) return false;

  try {
    // Node builds an Ed25519 key from a JWK holding the raw 32 bytes.
    const key = crypto.createPublicKey({
      key: { kty: "OKP", crv: "Ed25519", x: Buffer.from(publicKey, "hex").toString("base64url") },
      format: "jwk",
    });
    const message = Buffer.concat([Buffer.from(ts, "utf8"), raw]);
    return crypto.verify(null, message, key, Buffer.from(sig, "hex"));
  } catch {
    return false;
  }
}

function parseObject(raw) {
  try {
    const payload = JSON.parse(raw.toString("utf8"));
    return payload !== null && typeof payload === "object" && !Array.isArray(payload) ? payload : null;
  } catch {
    return null;
  }
}

/**
 * Webhook Events: verify, then parse. A PING (outer type 0) answers 204 with type "PING"; an event
 * (outer type 1) answers 204 with `type` = event.type, e.g. APPLICATION_AUTHORIZED. Discord does not
 * document an event id, so there is nothing to deduplicate on in the envelope.
 */
export function handleEvent(body, headers, { publicKey } = {}) {
  const raw = Buffer.isBuffer(body) ? body : Buffer.from(body ?? "", "utf8");
  if (!verify(raw, headers, publicKey)) return { status: 401 };
  const payload = parseObject(raw);
  if (payload === null) return { status: 400 };
  if (payload.type === 0) return { status: 204, type: "PING" };
  if (payload.type === 1) {
    const type = payload.event?.type;
    return typeof type === "string" ? { status: 204, type } : { status: 400 };
  }
  return { status: 400 };
}

/**
 * Interactions endpoint: verify, then parse. `type` is the integer interaction type and `id` the
 * interaction id. For a PING (type 1) `reply` is the exact body to answer with, {"type":1}; for
 * anything else it is null and you answer with a real interaction response within three seconds.
 */
export function handleInteraction(body, headers, { publicKey } = {}) {
  const raw = Buffer.isBuffer(body) ? body : Buffer.from(body ?? "", "utf8");
  if (!verify(raw, headers, publicKey)) return { status: 401 };
  const payload = parseObject(raw);
  if (payload === null || !Number.isInteger(payload.type) || typeof payload.id !== "string") return { status: 400 };
  return { status: 200, type: payload.type, id: payload.id, reply: payload.type === 1 ? '{"type":1}' : null };
}
