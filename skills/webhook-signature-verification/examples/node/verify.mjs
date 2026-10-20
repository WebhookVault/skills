// Webhook signature verification for the common scheme families. Node.js 18 or later, no
// dependencies. Every function takes the RAW body exactly as received (a Buffer, or a string you
// have not re-serialised), never a parsed object, and returns true or false without throwing.
//
// `now` is the current Unix time in seconds; it defaults to the real clock and is a parameter so
// tests can be deterministic. `tolerance` is how old (or how far in the future) a signed timestamp
// may be, in seconds. Five minutes is the common choice.

import crypto from "node:crypto";

const toBuffer = (body) => (Buffer.isBuffer(body) ? body : Buffer.from(String(body ?? ""), "utf8"));
const nowSeconds = () => Math.floor(Date.now() / 1000);

/** Constant-time comparison of two strings; false when either is missing or the lengths differ. */
export function safeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string") return false;
  const x = Buffer.from(a, "utf8");
  const y = Buffer.from(b, "utf8");
  return x.length === y.length && crypto.timingSafeEqual(x, y);
}

/** True when `timestamp` is whole Unix seconds within `tolerance` of `now`. */
export function isFresh(timestamp, now = nowSeconds(), tolerance = 300) {
  if (!/^\d{1,12}$/.test(String(timestamp ?? ""))) return false;
  return Math.abs(now - Number(timestamp)) <= tolerance;
}

const hmac = (algorithm, key, parts, encoding) => {
  const mac = crypto.createHmac(algorithm, key);
  for (const part of parts) mac.update(part);
  return mac.digest(encoding);
};

/**
 * HMAC over the raw body. `encoding` "hex" or "base64"; `prefix` such as "sha256=" when the
 * header carries one.
 */
export function verifyHmacBody({ body, signature, secret, encoding = "hex", prefix = "", algorithm = "sha256" }) {
  if (!secret || typeof signature !== "string") return false;
  const expected = prefix + hmac(algorithm, secret, [toBuffer(body)], encoding);
  return safeEqual(signature, expected);
}

/**
 * A timestamp and one or more signatures in one header, such as "t=1,v1=abc,v1=def" over
 * "<t>.<body>", or "ts=1;h1=abc" over "<ts>:<body>". Several signature entries are accepted, as
 * senders do during a secret rotation; any one matching is enough.
 */
export function verifyTimestampHeader({
  body, header, secret, now = nowSeconds(), tolerance = 300,
  pairSeparator = ",", timestampKey = "t", signatureKey = "v1", joiner = ".",
}) {
  if (!secret || typeof header !== "string") return false;
  const pairs = header.split(pairSeparator).map((p) => {
    const i = p.indexOf("=");
    return i < 0 ? [p.trim(), ""] : [p.slice(0, i).trim(), p.slice(i + 1).trim()];
  });
  const timestamps = pairs.filter(([k]) => k === timestampKey).map(([, v]) => v);
  if (timestamps.length !== 1 || !isFresh(timestamps[0], now, tolerance)) return false;
  const expected = hmac("sha256", secret, [Buffer.from(timestamps[0] + joiner, "utf8"), toBuffer(body)], "hex");
  return pairs.some(([k, v]) => k === signatureKey && safeEqual(v, expected));
}

/** A timestamp in its own header and a signature "v0=<hex>" over "v0:<timestamp>:<body>". */
export function verifyVersionedTimestamp({ body, timestamp, signature, secret, now = nowSeconds(), tolerance = 300, version = "v0" }) {
  if (!secret || !isFresh(timestamp, now, tolerance)) return false;
  const expected = `${version}=` + hmac("sha256", secret, [Buffer.from(`${version}:${timestamp}:`, "utf8"), toBuffer(body)], "hex");
  return safeEqual(signature, expected);
}

/**
 * Standard Webhooks: the secret is "whsec_" plus base64 key bytes; the signed content is
 * "<id>.<timestamp>.<body>"; the signature header holds space-separated "v1,<base64>" entries.
 */
export function verifyStandardWebhooks({ body, id, timestamp, signature, secret, now = nowSeconds(), tolerance = 300 }) {
  if (typeof secret !== "string" || !secret.startsWith("whsec_") || !id || typeof signature !== "string") return false;
  if (!isFresh(timestamp, now, tolerance)) return false;
  const key = Buffer.from(secret.slice("whsec_".length), "base64");
  if (key.length === 0) return false;
  const expected = hmac("sha256", key, [Buffer.from(`${id}.${timestamp}.`, "utf8"), toBuffer(body)], "base64");
  return signature.split(" ").some((entry) => {
    const comma = entry.indexOf(",");
    return comma > 0 && entry.slice(0, comma) === "v1" && safeEqual(entry.slice(comma + 1), expected);
  });
}

/**
 * HMAC-SHA1 over the full URL the sender called, followed by every form parameter name and value
 * sorted by name, base64. `url` must be the public URL configured at the sender, from your own
 * configuration, never rebuilt from the incoming request (a proxy changes scheme, host or port).
 */
export function verifyUrlForm({ url, params, signature, secret }) {
  if (!secret || typeof url !== "string" || typeof signature !== "string") return false;
  const names = Object.keys(params ?? {}).sort();
  const data = url + names.map((n) => n + String(params[n])).join("");
  return safeEqual(signature, hmac("sha1", secret, [Buffer.from(data, "utf8")], "base64"));
}

// DER prefix that wraps a raw 32-byte Ed25519 public key as SubjectPublicKeyInfo.
const ED25519_SPKI_PREFIX = Buffer.from("302a300506032b6570032100", "hex");

/** Ed25519 over "<timestamp><body>"; hex signature; the public key as 64 hex characters. */
export function verifyEd25519({ body, timestamp, signature, publicKey, now = nowSeconds(), tolerance = 300 }) {
  if (!/^[0-9a-fA-F]{64}$/.test(publicKey ?? "") || !/^[0-9a-fA-F]{128}$/.test(signature ?? "")) return false;
  if (!isFresh(timestamp, now, tolerance)) return false;
  try {
    const key = crypto.createPublicKey({ key: Buffer.concat([ED25519_SPKI_PREFIX, Buffer.from(publicKey, "hex")]), format: "der", type: "spki" });
    return crypto.verify(null, Buffer.concat([Buffer.from(String(timestamp), "utf8"), toBuffer(body)]), key, Buffer.from(signature, "hex"));
  } catch {
    return false;
  }
}

/** ECDSA P-256 with SHA-256 over "<timestamp><body>"; base64 DER signature; base64 SPKI public key. */
export function verifyEcdsaP256({ body, timestamp, signature, publicKey, now = nowSeconds(), tolerance = 300 }) {
  if (typeof publicKey !== "string" || typeof signature !== "string" || !isFresh(timestamp, now, tolerance)) return false;
  try {
    const key = crypto.createPublicKey({ key: Buffer.from(publicKey, "base64"), format: "der", type: "spki" });
    if (key.asymmetricKeyType !== "ec") return false;
    return crypto.verify("sha256", Buffer.concat([Buffer.from(String(timestamp), "utf8"), toBuffer(body)]), key, Buffer.from(signature, "base64"));
  } catch {
    return false;
  }
}

/** A shared token sent in a header (no signature at all), compared in constant time. */
export function verifySharedToken({ value, token }) {
  return Boolean(token) && safeEqual(value, token);
}
