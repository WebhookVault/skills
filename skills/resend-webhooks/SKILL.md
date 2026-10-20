---
name: resend-webhooks
description: Receives and verifies Resend webhooks: svix-signature (Standard Webhooks), svix-id dedupe, out-of-order events, retries, tested Node.js, Python and C# code. Use when handling Resend.
license: MIT
metadata:
  author: "webhookvault"
  version: "0.1.0"
  repository: "https://github.com/WebhookVault/skills"
---

# Resend webhooks

Resend posts email, contact and domain events to each webhook you add, signed in the Standard Webhooks way
with three headers: `svix-id`, `svix-timestamp` and `svix-signature`.

## When to use

- Writing or fixing a Resend webhook handler.
- Signatures that fail, a webhook Resend disabled, or `email.opened` arriving before `email.delivered`.

## Quick facts

<!-- facts:start (generated from data/providers/resend.json by tools/provider-facts.mjs; edit the data, not this block) -->
| | |
|---|---|
| Signature header | svix-signature, with svix-id and svix-timestamp |
| Scheme | HMAC-SHA256, base64, v1, prefix (Standard Webhooks) |
| Signed content | {svix-id}.{svix-timestamp}.{raw body} |
| Where the secret comes from | Webhook details page in the dashboard (whsec_...) |
| Timestamp tolerance | Five minutes either way (Resend's SDK) |
| Event name | type (top level), for example email.bounced |
| Delivery or event id | svix-id header (the same on retries) |
| Handshake | None |
| Expected response | 200 |
| Response deadline | Not stated |
| Retries | 8 attempts: at once, then 5 s, 5 min, 30 min, 2 h, 5 h, 10 h, 10 h |

Read from Resend's own pages on 2026-10-20. Every value, its source page and the sentence it came from: [references/facts.md](references/facts.md).
<!-- facts:end -->

## Verify every request, then parse

Resend's pages show the headers and point to libraries; the scheme itself is spelled out in Resend's own
SDK (sources in [references/facts.md](references/facts.md)). The key is the base64 part of the signing
secret after `whsec_`, decoded. The signed string is `svix-id`, a full stop, `svix-timestamp`, a full stop
and the raw body. `svix-signature` holds one or more `v1,<base64>` entries separated by spaces; any one
may match.

```js
import crypto from "node:crypto";

function verifyResend(rawBody, id, timestamp, signatures, secret, now = Math.floor(Date.now() / 1000)) {
  if (!id || !/^\d+$/.test(timestamp ?? "") || Math.abs(now - Number(timestamp)) > 300) return false;
  const key = Buffer.from(secret.replace(/^whsec_/, ""), "base64");
  const expected = crypto.createHmac("sha256", key).update(`${id}.${timestamp}.`).update(rawBody).digest("base64");
  return String(signatures ?? "").split(" ").some((entry) => {
    const [version, sig] = entry.split(",", 2);
    return version === "v1" && sig?.length === expected.length && crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(expected));
  });
}
```

Resend's SDKs verify for you (`resend.webhooks.verify`, `Webhooks.verify`); they allow 300 seconds of
clock difference. Full handlers with tests: [examples/](examples/README.md).

## Handling an event

- The event name is `type` (`email.delivered`, `email.bounced`, ...); the details are in `data`.
- Delivery is at least once. Deduplicate on the `svix-id` header: it stays the same when Resend retries.
- Order is not guaranteed: `email.opened` can arrive before `email.delivered`. Use `created_at` to decide
  which state is newer (see the webhook-event-ordering skill).

## Answering and retries

- Answer 200. A failed delivery is retried eight times on a growing schedule over about a day (details in
  the quick facts); a webhook that keeps failing is disabled and your team gets an email. Re-enable it
  from the Webhooks page.
- Any delivered message, failed or succeeded, can be replayed from the dashboard.
- Resend publishes the IP addresses webhooks come from, if you must allowlist; keep the signature check
  either way.

## Testing

- Trigger real events (send an email, add a contact) and replay messages from the dashboard.
- `examples/fixtures/vectors.json` is signed by the openssl command line: several signatures, the window
  edges, a changed `svix-id`, an unknown signature version.

## Using WebhookVault with Resend

What WebhookVault does with Resend requests is in the last section of
[references/facts.md](references/facts.md): it checks the `svix-*` headers with the `whsec_` secret you
paste and reads the event name from `type`. With an assistant connected to WebhookVault's MCP server,
these skills do the reading:

- An event that never arrived: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-debug-missing-webhook
- A signature verdict that says failed: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-check-verification
- Forwarded events your receiver refused: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-inspect-deliveries

## Related skills

- The Standard Webhooks scheme in general: https://github.com/WebhookVault/skills/tree/main/skills/webhook-signature-verification
- Out-of-order email events: https://github.com/WebhookVault/skills/tree/main/skills/webhook-event-ordering
- Wiring a handler into Express, FastAPI or ASP.NET Core: https://github.com/WebhookVault/skills/tree/main/skills/webhook-receiver-patterns
