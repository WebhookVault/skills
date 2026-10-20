---
name: lemonsqueezy-webhooks
description: Receives and verifies Lemon Squeezy webhooks: X-Signature, event names from the signed body, custom_data, retries, tested Node.js, Python and C# code. Use when handling Lemon Squeezy.
license: MIT
metadata:
  author: "webhookvault"
  version: "0.1.0"
  repository: "https://github.com/WebhookVault/skills"
---

# Lemon Squeezy webhooks

Lemon Squeezy posts orders, subscriptions, license keys and more to each webhook you create, signed with a
secret you chose for that webhook in the `X-Signature` header.

## When to use

- Writing or fixing a Lemon Squeezy webhook handler.
- Signatures that do not match, events that seem to arrive twice, or linking a purchase back to your user.

## Quick facts

<!-- facts:start (generated from data/providers/lemonsqueezy.json by tools/provider-facts.mjs; edit the data, not this block) -->
| | |
|---|---|
| Signature header | X-Signature |
| Scheme | HMAC-SHA256, hex |
| Signed content | The raw body |
| Where the secret comes from | A signing secret you choose (6 to 40 characters) |
| Timestamp tolerance | None (no timestamp is signed) |
| Event name | X-Event-Name header, and meta.event_name in the body |
| Delivery or event id | Not stated (data.id is the resource) |
| Handshake | None |
| Expected response | 200 only |
| Response deadline | Not stated |
| Retries | Up to three more times with back-off (for example 5 s, 25 s, 125 s) |

Read from Lemon Squeezy's own pages on 2026-10-20. Every value, its source page and the sentence it came from: [references/facts.md](references/facts.md).
<!-- facts:end -->

## Verify every request, then parse

`X-Signature` is the hex HMAC-SHA256 of the raw body with your signing secret (one you set, 6 to 40
characters; make it long and random).

```js
import crypto from "node:crypto";

function verifyLemonSqueezy(rawBody, header, secret) {
  if (typeof header !== "string") return false;
  const expected = crypto.createHmac("sha256", secret).update(rawBody).digest("hex");
  const a = Buffer.from(header), b = Buffer.from(expected);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}
```

Full handlers with tests: [examples/](examples/README.md). Lemon Squeezy's JavaScript SDK manages
webhooks but has no verification helper.

## Handling an event

- Read the event name from the signed body, `meta.event_name`. The `X-Event-Name` header says the same
  but is not covered by the signature; the examples refuse a request where the two disagree.
- `meta.custom_data` carries what you passed at checkout (for example your user id), on order,
  subscription and license key events.
- There is no event or delivery id. Several events are sent for one purchase (`order_created` with
  `subscription_created`, `license_key_created`; `subscription_payment_success` with
  `subscription_payment_recovered`), and `subscription_updated` follows every subscription change. Make
  handlers idempotent by state: store the resource's current status and `updated_at`, and apply only
  changes that are newer.
- The signature has no timestamp, so a captured request can be sent again; state-based handling keeps
  that harmless.

## Answering and retries

- Only 200 counts as success. Anything else is retried up to three more times with back-off (the docs'
  example: 5, 25 and 125 seconds), then dropped. Answer 200 quickly and queue the work.

## Testing

- Test mode stores send webhooks like live ones. From the dashboard you can simulate an event for a test
  order or subscription, see recent deliveries with their payloads, and resend them.
- `examples/fixtures/vectors.json` is signed by the openssl command line, including a header that
  disagrees with the body.

## Using WebhookVault with Lemon Squeezy

What WebhookVault does with Lemon Squeezy requests is in the last section of
[references/facts.md](references/facts.md): it checks `X-Signature` with the secret you paste and reads
the event name from `X-Event-Name`. With an assistant connected to WebhookVault's MCP server, these skills
do the reading:

- An event that never arrived: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-debug-missing-webhook
- A signature verdict that says failed: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-check-verification
- Forwarded events your receiver refused: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-inspect-deliveries

## Related skills

- Wiring a handler into Express, FastAPI or ASP.NET Core: https://github.com/WebhookVault/skills/tree/main/skills/webhook-receiver-patterns
- Applying only newer state: https://github.com/WebhookVault/skills/tree/main/skills/webhook-event-ordering
- Processing each change once: https://github.com/WebhookVault/skills/tree/main/skills/webhook-idempotency
