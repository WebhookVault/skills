// A webhook receiver skeleton for Express 5: cap the size, read the raw bytes, verify the signature,
// parse, deduplicate on the event id, acknowledge, and hand the work to a queue.
//
// The signature scheme here is a common one: header "Webhook-Signature: t=<unix>,v1=<hex>" with
// HMAC-SHA256 over "<t>.<raw body>". Swap verify() for your sender's scheme
// (see the webhook-signature-verification skill). The store and queue are in memory for the example;
// in production the store is a database table with a unique key and the queue is a real queue.

import crypto from "node:crypto";
import express from "express";

export const MAX_BODY_BYTES = 256 * 1024;
export const TOLERANCE_SECONDS = 300;

function safeEqual(a, b) {
  const x = Buffer.from(String(a ?? ""), "utf8");
  const y = Buffer.from(String(b ?? ""), "utf8");
  return x.length === y.length && crypto.timingSafeEqual(x, y);
}

export function verify(raw, header, secret, now = Math.floor(Date.now() / 1000)) {
  if (typeof header !== "string") return false;
  const pairs = header.split(",").map((p) => p.split("=", 2).map((s) => s.trim()));
  const stamps = pairs.filter(([k]) => k === "t").map(([, v]) => v);
  if (stamps.length !== 1 || !/^\d{1,12}$/.test(stamps[0])) return false;
  if (Math.abs(now - Number(stamps[0])) > TOLERANCE_SECONDS) return false;
  const expected = crypto.createHmac("sha256", secret).update(`${stamps[0]}.`).update(raw).digest("hex");
  return pairs.some(([k, v]) => k === "v1" && safeEqual(v, expected));
}

/** Remembers event ids. `firstTime(id)` is true only the first time an id is seen. */
export class MemoryStore {
  #seen = new Set();
  async firstTime(id) {
    if (this.#seen.has(id)) return false;
    this.#seen.add(id);
    return true;
  }
}

export function createApp({ secret, store = new MemoryStore(), enqueue, now }) {
  if (!secret) throw new Error("A signing secret is required (read it from the environment).");
  const app = express();

  // Only this route gets the raw body; a global express.json() would consume it first.
  app.post("/webhooks", express.raw({ type: () => true, limit: MAX_BODY_BYTES }), async (req, res) => {
    const raw = Buffer.isBuffer(req.body) ? req.body : Buffer.alloc(0);

    // 1. Authenticity before anything else: an unverified request must not touch state.
    if (!verify(raw, req.get("Webhook-Signature"), secret, now?.())) {
      return res.status(401).json({ error: "invalid_signature" });
    }

    // 2. Parse only after verifying, from the same bytes.
    let event;
    try {
      event = JSON.parse(raw.toString("utf8"));
    } catch {
      return res.status(400).json({ error: "invalid_json" });
    }
    if (typeof event?.id !== "string" || event.id.length === 0 || event.id.length > 200) {
      return res.status(400).json({ error: "missing_event_id" });
    }

    // 3. Deduplicate: the sender retries, so the same event can arrive more than once.
    if (!(await store.firstTime(event.id))) {
      return res.status(200).json({ received: true, duplicate: true });
    }

    // 4. Acknowledge fast; the work happens elsewhere. If the hand-off fails, answer 500 so the
    //    sender retries (and make the store forget the id; see the webhook-idempotency skill).
    try {
      await enqueue(event);
    } catch {
      return res.status(500).json({ error: "try_again" });
    }
    return res.status(200).json({ received: true });
  });

  // A body over the limit is refused with 413 by express.raw; answer it as JSON, never a stack.
  app.use((err, _req, res, _next) => {
    const status = err?.type === "entity.too.large" ? 413 : err?.status && err.status < 500 ? err.status : 500;
    res.status(status).json({ error: status === 413 ? "too_large" : "bad_request" });
  });

  return app;
}
