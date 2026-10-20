// Verifies and reads PayPal webhooks. Framework-free: pass the raw body bytes and the headers; wire it
// into Express, Fastify or anything else as shown in the webhook-receiver-patterns skill.
// Node.js 18+, no dependencies.
//
// PayPal signs "<PAYPAL-TRANSMISSION-ID>|<PAYPAL-TRANSMISSION-TIME>|<webhook id>|<crc32>", where crc32
// is the CRC-32 (IEEE, as zlib) of the raw body as an unsigned decimal number. The signature is RSA
// PKCS#1 v1.5 with SHA-256, base64 encoded, in PAYPAL-TRANSMISSION-SIG, and PAYPAL-AUTH-ALGO must be
// SHA256withRSA. The public key is the certificate at PAYPAL-CERT-URL, so that header is attacker
// controlled until proven otherwise: a certificate fetched from anywhere else would let anyone sign.
// PayPal's docs do not state a host rule, so this one is ours: the URL must be https, on paypal.com or a
// subdomain of it, with no userinfo and no non-default port. Only a URL that passes is ever fetched.
//
// Pass fetchCertificate(url), which returns the certificate as PEM text (it may be async). Cache the
// certificates by URL: they change rarely, and fetching on every webhook adds latency and a failure mode.
// A fetch that throws gives 500 so PayPal retries; it is not a verdict on the signature.

import crypto from "node:crypto";

export class CertificateFetchError extends Error {}

const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[n] = c >>> 0;
  }
  return table;
})();

/** CRC-32 (IEEE 802.3, the same value as zlib.crc32) of the bytes, as an unsigned integer. */
export function crc32(bytes) {
  let c = 0xffffffff;
  for (const b of bytes) c = CRC_TABLE[(c ^ b) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function header(headers, name) {
  const key = Object.keys(headers ?? {}).find((k) => k.toLowerCase() === name.toLowerCase());
  const value = key === undefined ? undefined : headers[key];
  return Array.isArray(value) ? value[0] : value;
}

/** True only for an https URL on paypal.com or a subdomain, with no userinfo and the default port. */
export function isTrustedCertificateUrl(value) {
  let url;
  try {
    url = new URL(value);
  } catch {
    return false;
  }
  if (url.protocol !== "https:" || url.username !== "" || url.password !== "" || url.port !== "") return false;
  const host = url.hostname;
  if (!/^[a-z0-9.-]+$/.test(host)) return false;
  return host === "paypal.com" || host.endsWith(".paypal.com");
}

function requireOptions(webhookId, fetchCertificate) {
  if (!webhookId) throw new Error("The PayPal webhook id is required (read it from the environment).");
  if (typeof fetchCertificate !== "function") throw new Error("fetchCertificate(url) is required.");
}

/**
 * True when the request carries a valid PayPal signature over these exact bytes. Throws
 * CertificateFetchError when the certificate could not be fetched (not a verdict on the signature).
 */
export async function verify(body, headers, { webhookId, fetchCertificate } = {}) {
  requireOptions(webhookId, fetchCertificate);
  const raw = Buffer.isBuffer(body) ? body : Buffer.from(body ?? "", "utf8");
  const id = header(headers, "PAYPAL-TRANSMISSION-ID");
  const time = header(headers, "PAYPAL-TRANSMISSION-TIME");
  const sig = header(headers, "PAYPAL-TRANSMISSION-SIG");
  const certUrl = header(headers, "PAYPAL-CERT-URL");
  const algo = header(headers, "PAYPAL-AUTH-ALGO");
  if (![id, time, sig, certUrl].every((v) => typeof v === "string" && v !== "")) return false;
  if (algo !== "SHA256withRSA") return false;
  if (!isTrustedCertificateUrl(certUrl)) return false;

  let pem;
  try {
    pem = await fetchCertificate(certUrl);
  } catch (err) {
    throw new CertificateFetchError(`Could not fetch the PayPal certificate: ${err?.message ?? err}`, { cause: err });
  }

  try {
    const key = new crypto.X509Certificate(pem).publicKey;
    if (key.asymmetricKeyType !== "rsa") return false;
    const signed = Buffer.from(`${id}|${time}|${webhookId}|${crc32(raw)}`, "utf8");
    return crypto.verify("sha256", signed, key, Buffer.from(sig, "base64"));
  } catch {
    return false; // not a certificate, or not usable for RSA
  }
}

/**
 * Handles one request: verify, then parse. Returns the HTTP status to answer with and, when the
 * request is accepted, the event name (`type`, event_type) and the id to deduplicate on (`id`, the
 * body's id). 500 means the certificate could not be fetched: PayPal will retry.
 */
export async function handle(body, headers, { webhookId, fetchCertificate } = {}) {
  requireOptions(webhookId, fetchCertificate);
  const raw = Buffer.isBuffer(body) ? body : Buffer.from(body ?? "", "utf8");
  let valid;
  try {
    valid = await verify(raw, headers, { webhookId, fetchCertificate });
  } catch (err) {
    if (err instanceof CertificateFetchError) return { status: 500 };
    throw err;
  }
  if (!valid) return { status: 401 };

  let payload;
  try {
    payload = JSON.parse(raw.toString("utf8"));
  } catch {
    return { status: 400 };
  }
  if (payload === null || typeof payload !== "object") return { status: 400 };
  if (typeof payload.event_type !== "string" || typeof payload.id !== "string") return { status: 400 };
  return { status: 200, type: payload.event_type, id: payload.id };
}
