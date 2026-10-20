---
name: woocommerce-webhooks
description: Receives and verifies WooCommerce webhooks: signature header, the unsigned ping, topics, auto-disable after failures, tested Node.js, Python and C# code. Use when handling WooCommerce.
license: MIT
metadata:
  author: "webhookvault"
  version: "0.1.0"
  repository: "https://github.com/WebhookVault/skills"
---

# WooCommerce webhooks

A WooCommerce store posts a JSON copy of an order, product, customer or coupon to each webhook whose
topic matches (`order.created`, `product.updated`, ...), signed with that webhook's secret in
`X-WC-Webhook-Signature`. The store sends them itself, from a background queue.

## When to use

- Writing or fixing the receiver for a WooCommerce webhook.
- A webhook that WooCommerce switched to Disabled, a save that failed on activation, or signatures that do
  not match.

## Quick facts

<!-- facts:start (generated from data/providers/woocommerce.json by tools/provider-facts.mjs; edit the data, not this block) -->
| | |
|---|---|
| Signature header | X-WC-Webhook-Signature |
| Scheme | HMAC-SHA256, base64 |
| Signed content | The raw body |
| Where the secret comes from | The webhook's Secret field (generated when left blank) |
| Timestamp tolerance | None (no timestamp is signed) |
| Event name | X-WC-Webhook-Topic header, for example order.updated |
| Delivery or event id | X-WC-Webhook-Delivery-ID header |
| Handshake | Unsigned ping, body webhook_id=<id>, on activation; answer 200 |
| Expected response | 2xx (also 301 and 302) |
| Response deadline | 60 seconds (WooCommerce source) |
| Retries | None in the source; disabled after more than five consecutive failures |

Read from WooCommerce's own pages on 2026-10-20. Every value, its source page and the sentence it came from: [references/facts.md](references/facts.md).
<!-- facts:end -->

## Verify every request, except the ping

The signature is the base64 HMAC-SHA256 of the raw body with the webhook's secret.

```js
import crypto from "node:crypto";

function verifyWooCommerce(rawBody, header, secret) {
  if (typeof header !== "string") return false;
  const expected = crypto.createHmac("sha256", secret).update(rawBody).digest("base64");
  const a = Buffer.from(header), b = Buffer.from(expected);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}
```

When a webhook is first saved as Active, WooCommerce sends a ping: the body `webhook_id=<id>`, not JSON,
with no signature. It must get exactly 200 or the save reports an error. Answer 200 to that exact body
without a signature and do nothing else; refuse every other unsigned request. Full handlers with tests:
[examples/](examples/README.md).

## Handling a webhook

- The topic is the `X-WC-Webhook-Topic` header (also split into `-Resource` and `-Event`); the body is the
  same as the REST API's representation of the resource.
- `X-WC-Webhook-Delivery-ID` identifies a delivery. The signature covers only the body, not these headers,
  and nothing signed carries a time, so a captured request can be sent again: compare the resource's
  `date_modified_gmt` with what you have before overwriting.
- WooCommerce coalesces identical pending deliveries within 10 minutes, so quick repeated changes to one
  record can produce fewer webhooks than changes. Fetch the resource when you need its current state.

## Answering, failures and disabling

- WooCommerce waits up to 60 seconds and does not follow redirects. Its source counts 200 to 302 as
  success; the REST docs say 2xx (see [references/facts.md](references/facts.md)). Answer 200.
- The source has no retries: a failed delivery is not sent again. After more than five consecutive
  failures WooCommerce sets the webhook to Disabled, and someone must edit it back to Active. Monitor for
  gaps and reconcile through the REST API.
- The docs and the source disagree on several details (the default secret, the background runner, the
  delivery id, success codes); all six are listed in [references/facts.md](references/facts.md).

## Testing

- WooCommerce has no send-test button. Saving a webhook as Active sends the ping; WooCommerce > Status >
  Logs (source `webhooks-delivery`) records each delivery and its response.
- `examples/fixtures/vectors.json` is signed by the openssl command line, including the unsigned ping and an
  almost-ping that must be refused.

## Using WebhookVault with WooCommerce

What WebhookVault does with WooCommerce requests is in the last section of
[references/facts.md](references/facts.md): it checks `X-WC-Webhook-Signature` with the secret you paste
and reads the topic header. With an assistant connected to WebhookVault's MCP server, these skills do the
reading:

- A webhook that never arrived: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-debug-missing-webhook
- A signature verdict that says failed: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-check-verification
- Forwarded webhooks your receiver refused: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-inspect-deliveries

## Related skills

- Wiring a handler into Express, FastAPI or ASP.NET Core: https://github.com/WebhookVault/skills/tree/main/skills/webhook-receiver-patterns
- Applying only newer changes: https://github.com/WebhookVault/skills/tree/main/skills/webhook-event-ordering
- Other signature schemes: https://github.com/WebhookVault/skills/tree/main/skills/webhook-signature-verification
