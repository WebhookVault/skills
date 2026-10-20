---
name: paddle-webhooks
description: Receives and verifies Paddle Billing webhooks: Paddle-Signature ts and h1, five second window, event_id dedupe, ordering, retries, tested code. Use when handling Paddle events.
license: MIT
metadata:
  author: "webhookvault"
  version: "0.1.0"
  repository: "https://github.com/WebhookVault/skills"
---

# Paddle webhooks

Paddle Billing posts each event to every notification destination that subscribes to it, signed with that
destination's secret key in the `Paddle-Signature` header.

## When to use

- Writing or fixing a Paddle Billing webhook handler.
- Signatures that fail, events processed twice, or a subscription in the wrong state after events arrived
  out of order.

## Quick facts

<!-- facts:start (generated from data/providers/paddle.json by tools/provider-facts.mjs; edit the data, not this block) -->
| | |
|---|---|
| Signature header | Paddle-Signature |
| Scheme | HMAC-SHA256, hex; the secret string itself is the key |
| Signed content | {ts}:{raw body} |
| Where the secret comes from | The notification destination's secret key (pdl_ntfset_...) |
| Timestamp tolerance | Five seconds in Paddle's SDKs; "reject events that are too old" |
| Event name | event_type (top level), entity.action |
| Delivery or event id | event_id (evt_...), the same on every retry |
| Handshake | None |
| Expected response | 200 |
| Response deadline | 5 seconds |
| Retries | Live: up to 60 attempts over about two days; sandbox: 3 in about two minutes |

Read from Paddle's own pages on 2026-10-20. Every value, its source page and the sentence it came from: [references/facts.md](references/facts.md).
<!-- facts:end -->

## Verify every request, then parse

`Paddle-Signature` is `ts=<unix>;h1=<hex>`, with more than one `h1` while a secret is being changed. The
signed string is `ts`, a colon and the raw body; the key is the destination's secret key exactly as shown
(`pdl_ntfset_...`), not decoded.

```js
import crypto from "node:crypto";

function verifyPaddle(rawBody, header, secretKey, now = Math.floor(Date.now() / 1000)) {
  const pairs = String(header ?? "").split(";").map((p) => p.split("=", 2));
  const ts = pairs.filter(([k]) => k === "ts").map(([, v]) => v);
  if (ts.length !== 1 || !/^\d+$/.test(ts[0]) || Math.abs(now - Number(ts[0])) > 5) return false;
  const expected = crypto.createHmac("sha256", secretKey).update(`${ts[0]}:`).update(rawBody).digest("hex");
  return pairs.some(([k, v]) => k === "h1" && v?.length === expected.length &&
    crypto.timingSafeEqual(Buffer.from(v), Buffer.from(expected)));
}
```

Paddle's SDKs verify for you and allow five seconds between `ts` and your clock (`webhooks.unmarshal`,
`Verifier().verify`; see [references/facts.md](references/facts.md)). Five seconds needs an accurate
clock: keep NTP on. Full handlers with tests: [examples/](examples/README.md).

## Handling an event

- The event name is `event_type` (`transaction.completed`, `subscription.updated`, ...). Deduplicate on
  `event_id`: it stays the same across retries and across destinations. `notification_id` identifies the
  delivery to one destination.
- Order is not guaranteed. Store `occurred_at` per entity and ignore an event older than what you have
  (see the webhook-event-ordering skill). A checkout typically produces `transaction.created`,
  `customer.created`, `address.created`, `transaction.paid`, `subscription.created` and
  `transaction.completed`.
- `transaction.paid` is the earliest point a payment is known to have succeeded; `transaction.completed`
  follows once Paddle has finished processing.

## Answering and retries

- Answer 200 within five seconds, before any processing; serverless cold starts are a common cause of
  timeouts.
- Live accounts retry up to 60 times over about two days; sandbox accounts 3 times within about two
  minutes. A notification that runs out of attempts is marked failed and can be replayed through the API.
- Paddle publishes its sending IP addresses (different for sandbox and live) and sends a `Paddle` user
  agent; allow them past any firewall or bot check on the webhook path.

## Testing

- The webhook simulator (Paddle > Events > Simulations, or the API) sends single events or whole
  scenarios to destinations whose usage type includes simulations.
- `examples/fixtures/vectors.json` is signed by the openssl command line: two `h1` values, the five second
  edges, a re-serialised body. Paddle's docs print no complete worked example to add.

## Using WebhookVault with Paddle

What WebhookVault does with Paddle requests is in the last section of
[references/facts.md](references/facts.md): it checks `Paddle-Signature` with the secret key you paste and
reads the event name from `event_type`. Its own timestamp allowance is wider than Paddle's five seconds,
so a request it marks verified can still be refused by an SDK if the clocks differ. With an assistant
connected to WebhookVault's MCP server, these skills do the reading:

- An event that never arrived: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-debug-missing-webhook
- A signature verdict that says failed: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-check-verification
- Forwarded events your receiver refused: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-inspect-deliveries

## Related skills

- Wiring a handler into Express, FastAPI or ASP.NET Core: https://github.com/WebhookVault/skills/tree/main/skills/webhook-receiver-patterns
- Out-of-order events: https://github.com/WebhookVault/skills/tree/main/skills/webhook-event-ordering
- Deduplicating on `event_id`: https://github.com/WebhookVault/skills/tree/main/skills/webhook-idempotency
