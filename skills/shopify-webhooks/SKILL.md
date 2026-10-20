---
name: shopify-webhooks
description: Receives and verifies Shopify webhooks: HMAC header, topics, webhook ids, 5 second limit, retries and removal, compliance topics, tested code. Use when building Shopify app webhooks.
license: MIT
metadata:
  author: "webhookvault"
  version: "0.1.0"
  repository: "https://github.com/WebhookVault/skills"
---

# Shopify webhooks

A Shopify app subscribes to topics (`orders/create`, `products/update`, ...) and Shopify posts each
change to the app's endpoint, signed with the app's client secret in `X-Shopify-Hmac-Sha256`.

## When to use

- Writing or fixing a Shopify app's webhook handler, including the mandatory compliance topics.
- HMAC checks that fail, subscriptions that vanished, or events that arrive twice or out of order.

## Quick facts

<!-- facts:start (generated from data/providers/shopify.json by tools/provider-facts.mjs; edit the data, not this block) -->
| | |
|---|---|
| Signature header | X-Shopify-Hmac-Sha256 |
| Scheme | HMAC-SHA256, base64 |
| Signed content | The raw body |
| Where the secret comes from | The app's client secret (one per app) |
| Timestamp tolerance | None (no timestamp is signed) |
| Event name | X-Shopify-Topic header, for example orders/create |
| Delivery or event id | X-Shopify-Webhook-Id (X-Shopify-Event-Id is shared per merchant action) |
| Handshake | None |
| Expected response | 200 to 299; redirects are errors |
| Response deadline | 1 second to connect, 5 seconds in all |
| Retries | 8 retries over 4 hours, then Admin API subscriptions are deleted |

Read from Shopify's own pages on 2026-10-20. Every value, its source page and the sentence it came from: [references/facts.md](references/facts.md).
<!-- facts:end -->

## Verify every request, then parse

The header is the base64 HMAC-SHA256 of the raw body, keyed with the app's client secret (one secret for
every shop and topic). Read the raw body before any parser runs.

```js
import crypto from "node:crypto";

function verifyShopify(rawBody, header, clientSecret) {
  if (typeof header !== "string") return false;
  const expected = crypto.createHmac("sha256", clientSecret).update(rawBody).digest("base64");
  const a = Buffer.from(header), b = Buffer.from(expected);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}
```

```python
import base64, hashlib, hmac

def verify_shopify(raw_body: bytes, header: str, client_secret: str) -> bool:
    expected = base64.b64encode(hmac.new(client_secret.encode(), raw_body, hashlib.sha256).digest())
    return isinstance(header, str) and hmac.compare_digest(header.encode(), expected)
```

Shopify's app libraries verify for you (`shopify.webhooks.validate`, `authenticate.webhook`; see
[references/facts.md](references/facts.md)). Full handlers with tests: [examples/](examples/README.md).
Header names may arrive in lower case over HTTP/2; look them up without regard to case.

## Handling a webhook

- The topic is the `X-Shopify-Topic` header; the body does not name it.
- Deduplicate on `X-Shopify-Webhook-Id` (one per delivery). `X-Shopify-Event-Id` is shared by every
  delivery one merchant action produced, so two subscriptions to a topic give two webhook ids and one event
  id.
- Order is not guaranteed, even within one topic (`products/update` can come before `products/create`):
  compare `updated_at` or `X-Shopify-Triggered-At` before overwriting newer data.
- The signature covers only the body, not the topic or id headers, and no signed time. A captured request
  can be sent again; deduplication on the webhook id and the `updated_at` comparison above keep that
  harmless.
- Shopify does not guarantee delivery: run a reconciliation job that queries what changed.

## Answering, retries and removal

- Shopify allows 1 second to connect and 5 seconds for the whole request; answer 200 and queue the work.
  Redirects count as errors.
- A failed delivery is retried 8 times over 4 hours. After 8 consecutive failures, a subscription made
  through the Admin API is deleted (warning emails go to the app's emergency developer address);
  subscriptions defined in `shopify.app.toml` are not deleted, though Shopify's pages differ on this
  (see [references/facts.md](references/facts.md)).

## Compliance topics

Apps in the Shopify App Store must handle `customers/data_request`, `customers/redact` and `shop/redact`:
subscribe in the app configuration (`compliance_topics`), answer 401 to an invalid HMAC and 2xx otherwise,
then complete the request within 30 days.

## Testing

- `shopify app webhook trigger` sends a synthetic webhook to an address you give; it does not test your
  real subscription. The Dev Dashboard shows 7 days of delivery logs.
- `examples/fixtures/vectors.json` is signed by the openssl command line, including lower-case headers and
  a compliance topic. Shopify's docs print no complete worked example to add.

## Using WebhookVault with Shopify

What WebhookVault does with Shopify requests is in the last section of
[references/facts.md](references/facts.md): it checks `X-Shopify-Hmac-Sha256` with the secret you paste
and reads the topic header. With an assistant connected to WebhookVault's MCP server, these skills do the
reading:

- A webhook that never arrived: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-debug-missing-webhook
- A signature verdict that says failed: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-check-verification
- Forwarded webhooks your receiver refused: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-inspect-deliveries

## Related skills

- Wiring a handler into Express, FastAPI or ASP.NET Core: https://github.com/WebhookVault/skills/tree/main/skills/webhook-receiver-patterns
- Out-of-order updates: https://github.com/WebhookVault/skills/tree/main/skills/webhook-event-ordering
- Deduplicating on the webhook id: https://github.com/WebhookVault/skills/tree/main/skills/webhook-idempotency
