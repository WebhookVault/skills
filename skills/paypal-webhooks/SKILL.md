---
name: paypal-webhooks
description: Receives and verifies PayPal webhooks: certificate signature with CRC32, safe certificate fetching, the verify API, retries, tested Node.js, Python and C# code. Use when handling PayPal.
license: MIT
metadata:
  author: "webhookvault"
  version: "0.1.0"
  repository: "https://github.com/WebhookVault/skills"
---

# PayPal webhooks

PayPal posts each event to every listener URL an app subscribes, signed with PayPal's private key. There
is no shared secret: you check the signature with the public key in PayPal's certificate, or ask PayPal's
API to check it for you.

## When to use

- Writing or fixing a PayPal REST webhook listener.
- Verification that always fails, or events from the simulator that cannot be verified.

## Quick facts

<!-- facts:start (generated from data/providers/paypal.json by tools/provider-facts.mjs; edit the data, not this block) -->
| | |
|---|---|
| Signature header | PAYPAL-TRANSMISSION-SIG, with -ID, -TIME, PAYPAL-CERT-URL, PAYPAL-AUTH-ALGO |
| Scheme | RSA with SHA-256 (SHA256withRSA), checked with PayPal's certificate; no shared secret |
| Signed content | {transmission id}\|{transmission time}\|{webhook id}\|{CRC32 of the raw body, decimal} |
| Where the secret comes from | No secret: the webhook ID from the app's settings, and the certificate at PAYPAL-CERT-URL |
| Timestamp tolerance | Not stated |
| Event name | event_type (top level), for example PAYMENT.CAPTURE.COMPLETED |
| Delivery or event id | id (WH-...) in the body |
| Handshake | None |
| Expected response | 2xx |
| Response deadline | Not stated |
| Retries | Up to 25 times over 3 days |

Read from PayPal's own pages on 2026-10-20. Every value, its source page and the sentence it came from: [references/facts.md](references/facts.md).
<!-- facts:end -->

## What is signed

The signed string is four values joined by `|`:

1. `PAYPAL-TRANSMISSION-ID` header
2. `PAYPAL-TRANSMISSION-TIME` header
3. your webhook ID, from the app's webhook settings (it is not in the request: store it)
4. the CRC-32 of the raw body, as an unsigned decimal number

The signature in `PAYPAL-TRANSMISSION-SIG` is base64 RSA with SHA-256 (`PAYPAL-AUTH-ALGO` says
`SHA256withRSA`), checked with the public key of the certificate at `PAYPAL-CERT-URL`.

## Only fetch PayPal's certificate

The certificate URL arrives in the request, so a forger can point it at their own certificate and sign
with their own key. PayPal's docs do not say which hosts serve its certificates, and its sample listener
downloads whatever URL it is given. The examples here apply a rule of our own: fetch only `https` URLs on
`paypal.com` or a subdomain of it, refuse everything else before any network call, and cache each
certificate by URL. If you cannot apply such a rule, use the verify API instead.

## Two ways to verify

- **Yourself** (PayPal's preferred method: faster, no extra API call): the steps above. Full handlers
  with tests: [examples/](examples/README.md).
- **PayPal's API**: `POST /v1/notifications/verify-webhook-signature` with the five header values, your
  webhook ID and the event exactly as received; the answer's `verification_status` is `SUCCESS` or
  `FAILURE` (fields in [references/facts.md](references/facts.md)). It needs an access token, and it cannot
  verify simulator events.

## Handling an event

- The event name is `event_type` (`PAYMENT.CAPTURE.COMPLETED`, ...); deduplicate on the body's `id`
  (`WH-...`). `resource_version` tells you which shape `resource` has.
- PayPal states no timestamp window and retries for 3 days, so the examples check none; deduplication on
  `id` is what stops a replayed request counting twice.
- `PAYMENT.CAPTURE.DENIED` and `PAYMENT.CAPTURE.DECLINED` both appear in PayPal's event list (Payments v1
  and v2); handle both if you take card payments through both APIs.

## Answering and retries

- Answer 2xx. Anything else is retried up to 25 times over 3 days, then marked Failed; failed events can
  be resent from the Webhook Events dashboard.
- PayPal delivers only to HTTPS on port 443.

## Testing

- The webhooks simulator posts mock events to any HTTPS listener. Mock events use the literal webhook ID
  `WEBHOOK_ID` for self verification and cannot be checked with the verify API.
- Sandbox apps produce real test events from sandbox transactions.
- `examples/fixtures/vectors.json` is signed by the openssl command line with a certificate made for that
  run: certificate URLs on another host, a look-alike host and plain http (all refused before any fetch),
  a changed body (the CRC-32 changes) and another webhook ID.

## Using WebhookVault with PayPal

WebhookVault does not check PayPal's signature yet: a captured PayPal request shows the verdict as
unverifiable with the scheme named, and the receiver must verify. The rest of what WebhookVault does with
PayPal requests is in the last section of [references/facts.md](references/facts.md). With an assistant
connected to WebhookVault's MCP server, these skills do the reading:

- An event that never arrived: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-debug-missing-webhook
- The unverifiable verdict explained: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-check-verification
- Forwarded events your receiver refused: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-inspect-deliveries

## Related skills

- Wiring a handler into Express, FastAPI or ASP.NET Core: https://github.com/WebhookVault/skills/tree/main/skills/webhook-receiver-patterns
- Deduplicating on the event id: https://github.com/WebhookVault/skills/tree/main/skills/webhook-idempotency
- Other signature schemes: https://github.com/WebhookVault/skills/tree/main/skills/webhook-signature-verification
