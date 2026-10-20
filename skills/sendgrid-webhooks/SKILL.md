---
name: sendgrid-webhooks
description: Receives and verifies SendGrid Event Webhook batches: ECDSA signature over timestamp and body, event arrays, sg_event_id dedupe, retries, tested code. Use when handling SendGrid email events.
license: MIT
metadata:
  author: "webhookvault"
  version: "0.1.0"
  repository: "https://github.com/WebhookVault/skills"
---

# SendGrid webhooks

SendGrid's Event Webhook posts what happened to your email (processed, delivered, opened, bounced,
...) to your URL in batches: one request carries a JSON array of events. With the Signed Event Webhook
turned on, each request is signed with SendGrid's private key and you verify it with a public key.

## When to use

- Writing or fixing the handler behind a SendGrid Event Webhook Post URL.
- Turning on signature verification, or signatures that never verify.
- Duplicate or missing email events.

## Quick facts

<!-- facts:start (generated from data/providers/sendgrid.json by tools/provider-facts.mjs; edit the data, not this block) -->
| | |
|---|---|
| Signature header | X-Twilio-Email-Event-Webhook-Signature, with X-Twilio-Email-Event-Webhook-Timestamp |
| Scheme | ECDSA with SHA-256, base64 signature (P-256 key in the official helpers) |
| Signed content | {timestamp}{raw body}, no separator |
| Where the secret comes from | Verification public key, shown after enabling Signed Event Webhook and saving |
| Timestamp tolerance | Not stated |
| Event name | event, on each object in the array |
| Delivery or event id | sg_event_id, on each event |
| Handshake | None |
| Expected response | 2xx |
| Response deadline | Not stated |
| Retries | Increasing intervals for up to 24 hours per event |

Read from SendGrid's own pages on 2026-10-20. Every value, its source page and the sentence it came from: [references/facts.md](references/facts.md).
<!-- facts:end -->

## Turn signing on first

Signing is off until you enable it in the Event Webhook's security settings and save; the
verification key appears only after saving. Without it there is nothing to check, and anyone who knows
the URL can post fake events. A separate OAuth option sends a bearer token instead (details in
[references/facts.md](references/facts.md)).

## Verify every batch, then parse

The signed bytes are the timestamp header value followed by the raw body, with no separator. The body
SendGrid sends ends with a carriage return and newline; keep it.

```js
import crypto from "node:crypto";

const publicKey = crypto.createPublicKey({                      // once, at start-up
  key: Buffer.from(process.env.SENDGRID_WEBHOOK_PUBLIC_KEY, "base64"), format: "der", type: "spki",
});

function verifySendGrid(rawBody, signature, timestamp) {
  if (typeof signature !== "string" || typeof timestamp !== "string") return false;
  const signed = Buffer.concat([Buffer.from(timestamp, "utf8"), rawBody]);
  try { return crypto.verify("sha256", signed, publicKey, Buffer.from(signature, "base64")); }
  catch { return false; }
}
```

```python
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

def verify_sendgrid(public_key, raw_body: bytes, signature: str, timestamp: str) -> bool:
    try:
        public_key.verify(base64.b64decode(signature, validate=True),
                          timestamp.encode() + raw_body, ec.ECDSA(hashes.SHA256()))
        return True
    except Exception:
        return False
```

SendGrid's libraries include an `EventWebhook` helper for this (names in
[references/facts.md](references/facts.md)). Full handlers with tests: [examples/](examples/README.md).

## Handling a batch

- Parse the array and treat each event on its own: its name is `event`, its id is `sg_event_id`.
- Duplicates happen; SendGrid says to deduplicate on `sg_event_id`. Insert the id and skip the event
  when it is already there (see the webhook-idempotency skill).
- Answer 2xx once the batch is stored. A non-2xx answer makes SendGrid retry the whole batch, for up
  to 24 hours, so one bad event must not fail the others: store what you cannot process and move on.
- Expect bursts: a busy account can post many batches a second.

## On the timestamp

The timestamp is signed, but SendGrid states no window for it and retries for up to 24 hours. The
examples here apply no age limit, because one could refuse SendGrid's own retries; `sg_event_id`
deduplication is what stops a replayed batch from counting twice.

## Pitfalls

- A JSON parser that runs first and re-serialises the body breaks the signature (and drops the
  trailing newline).
- The event name for a spam complaint: the docs' table writes `spam report`, the example payload
  `spamreport`. Accept both.
- Turning verification off and saving deletes the key pair; turning it on again makes a new key.
- Do not filter SendGrid by IP: it publishes no ranges and says its addresses change often.

## Testing

- SendGrid's Test Your Integration button posts example events; it cannot test the signature until
  the webhook has been saved with signing on.
- `examples/fixtures/vectors.json` is signed by the openssl command
  line with a P-256 key made for that run, including a body missing its trailing newline.

## Using WebhookVault with SendGrid

What WebhookVault does with SendGrid requests is in the last section of
[references/facts.md](references/facts.md): it verifies the signature with the public key you paste
and reads the event name from each event. With an assistant connected to WebhookVault's MCP server,
these skills do the reading:

- Events that never arrived: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-debug-missing-webhook
- A signature verdict that says failed: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-check-verification
- Forwarded batches your receiver refused: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-inspect-deliveries

## Related skills

- Wiring a handler into Express, FastAPI or ASP.NET Core: https://github.com/WebhookVault/skills/tree/main/skills/webhook-receiver-patterns
- Deduplicating on `sg_event_id`: https://github.com/WebhookVault/skills/tree/main/skills/webhook-idempotency
- Other signature schemes: https://github.com/WebhookVault/skills/tree/main/skills/webhook-signature-verification
