---
name: stripe-webhooks
description: Receives and verifies Stripe webhooks: Stripe-Signature t and v1, secret rolls, retries, duplicates, ordering, tested Node.js, Python and C# code. Use when handling Stripe events.
license: MIT
metadata:
  author: "webhookvault"
  version: "0.1.0"
  repository: "https://github.com/WebhookVault/skills"
---

# Stripe webhooks

Stripe sends an Event to each endpoint (Stripe now calls them event destinations) that listens for its
type, signed with that endpoint's signing secret in the `Stripe-Signature` header.

## When to use

- Writing or fixing a Stripe webhook handler, for your own account or a Connect platform.
- "No signatures found matching the expected signature", or verification failing only in production.
- Events processed twice, out of order, or not at all.

## Quick facts

<!-- facts:start (generated from data/providers/stripe.json by tools/provider-facts.mjs; edit the data, not this block) -->
| | |
|---|---|
| Signature header | Stripe-Signature |
| Scheme | HMAC-SHA256, hex; use only v1 signatures |
| Signed content | {t}.{raw body} |
| Where the secret comes from | Endpoint signing secret (whsec_...), per endpoint, test and live differ |
| Timestamp tolerance | Five minutes in Stripe's libraries; every retry is signed afresh |
| Event name | type (top level) |
| Delivery or event id | id (evt_...) in the body |
| Handshake | None |
| Expected response | 2xx; redirects count as failures |
| Response deadline | Not stated ("return quickly") |
| Retries | Live: up to three days with exponential back-off; sandbox: three over a few hours |

Read from Stripe's own pages on 2026-10-20. Every value, its source page and the sentence it came from: [references/facts.md](references/facts.md).
<!-- facts:end -->

## Verify every request, then parse

`Stripe-Signature` looks like `t=1760000000,v1=<hex>,v1=<hex>,v0=<hex>`. The signed string is the `t`
value, a full stop and the raw body. Accept the request when any `v1` matches; ignore `v0` and anything
else.

```js
import crypto from "node:crypto";

function verifyStripe(rawBody, header, secret, now = Math.floor(Date.now() / 1000)) {
  const pairs = String(header ?? "").split(",").map((p) => p.split("=", 2));
  const ts = pairs.filter(([k]) => k === "t").map(([, v]) => v);
  if (ts.length !== 1 || !/^\d+$/.test(ts[0]) || Math.abs(now - Number(ts[0])) > 300) return false;
  const expected = crypto.createHmac("sha256", secret).update(`${ts[0]}.`).update(rawBody).digest("hex");
  return pairs.some(([k, v]) => k === "v1" && v?.length === expected.length &&
    crypto.timingSafeEqual(Buffer.from(v), Buffer.from(expected)));
}
```

Stripe's own libraries do this (`stripe.webhooks.constructEvent`, `construct_event`,
`EventUtility.ConstructEvent`; exact names in [references/facts.md](references/facts.md)) and are the
usual choice. The examples here implement the rule so you can see and test it:
[examples/](examples/README.md).

## Handling an event

- The event name is `type`, the id to deduplicate on is the event `id` (`evt_...`). Stripe says
  duplicates happen; record processed ids and skip repeats (see the webhook-idempotency skill).
- Order is not guaranteed and `created` has one-second resolution, so never order by it. When an event
  arrives about an object you do not have yet, fetch the object from the API (see the
  webhook-event-ordering skill).
- A snapshot event's `data.object` can be stale by the time you act; fetch the current object before a
  decision that matters. Thin events carry only a reference and always need the fetch; they go to their
  own endpoint.
- Connect: events for connected accounts carry a top-level `account`, and a production Connect endpoint
  receives test events too. Check `livemode`.

## Answering and retries

- Answer 2xx before doing slow work. Redirects count as failures, so register the final URL.
- Live mode retries for up to three days with exponential back-off; sandbox retries three times over a
  few hours. Each retry is signed again with a new timestamp, so a five-minute window never blocks a
  genuine retry.
- A manual resend does not cancel automatic retries: answer 2xx to an event you already processed.

## Pitfalls

- The wrong secret is the most common failure: each endpoint has its own, test and live differ, and the
  Stripe CLI uses its own.
- Rolling the secret: for up to 24 hours both secrets sign, so the header carries two `v1` values. Code
  that reads only the first fails half the time.
- Body parsers: with Express, mount the webhook route with `express.raw` before `express.json`; in Rails
  or Django exempt the route from CSRF protection.
- Stripe can, rarely, fail to create an event; poll the resource for anything that must not be missed.

## Testing

- `stripe trigger <event>` creates test objects and fires the events they cause; Dashboard and CLI can
  resend past events.
- `examples/fixtures/vectors.json` is signed by the openssl command line: a fake `v0`, two `v1`
  signatures during a roll, the window edges, a re-serialised body. Stripe's docs print no complete worked
  example to add.
- To see exactly what Stripe sends, add a capture URL as an event destination, then send the captured
  request to your handler with a test secret.

## Using WebhookVault with Stripe

What WebhookVault does with Stripe requests is in the last section of
[references/facts.md](references/facts.md): it checks `Stripe-Signature` with the endpoint secret you
paste and reads the event name from `type`. With an assistant connected to WebhookVault's MCP server,
these skills do the reading:

- An event that never arrived: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-debug-missing-webhook
- A signature verdict that says failed: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-check-verification
- Forwarded events your receiver refused: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-inspect-deliveries

## Related skills

- Wiring a handler into Express, FastAPI or ASP.NET Core: https://github.com/WebhookVault/skills/tree/main/skills/webhook-receiver-patterns
- Deduplicating on the event id: https://github.com/WebhookVault/skills/tree/main/skills/webhook-idempotency
- Out-of-order events: https://github.com/WebhookVault/skills/tree/main/skills/webhook-event-ordering
