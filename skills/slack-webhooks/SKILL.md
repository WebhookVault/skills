---
name: slack-webhooks
description: Receives and verifies Slack Events API and interactivity requests: v0 signature, url_verification, 3 second answers, retries, tested Node.js, Python and C# code. Use when building a Slack request URL.
license: MIT
metadata:
  author: "webhookvault"
  version: "0.1.0"
  repository: "https://github.com/WebhookVault/skills"
---

# Slack webhooks

Slack sends Events API events and interactivity payloads (buttons, shortcuts, modals) as HTTP POSTs to
the Request URL you register for your app, and signs each one with the app's signing secret.

## When to use

- Writing or fixing the handler behind a Slack app's Event Subscriptions or Interactivity Request URL.
- Slack says the Request URL did not verify, events stopped, or the same event arrives twice.
- Checking a Slack signature by hand.

## Quick facts

<!-- facts:start (generated from data/providers/slack.json by tools/provider-facts.mjs; edit the data, not this block) -->
| | |
|---|---|
| Signature header | X-Slack-Signature, with X-Slack-Request-Timestamp |
| Scheme | HMAC-SHA256, hex, prefixed v0= |
| Signed content | v0:{timestamp}:{raw body} |
| Where the secret comes from | Signing Secret, app settings > Basic Information |
| Timestamp tolerance | Five minutes either way (Slack's example) |
| Event name | event.type (the top-level type is event_callback or url_verification) |
| Delivery or event id | event_id (top level) |
| Handshake | url_verification: answer 200 with the challenge value |
| Expected response | 2xx (interactions: 200) |
| Response deadline | 3 seconds |
| Retries | 3 retries: almost at once, after 1 minute, after 5 minutes (opt-in hourly for 24 hours) |

Read from Slack's own pages on 2026-10-20. Every value, its source page and the sentence it came from: [references/facts.md](references/facts.md).
<!-- facts:end -->

## Verify every request, then parse

The signature covers the timestamp and the exact bytes Slack sent. Read the raw body before any JSON or
form parser touches it, and compare in constant time.

```js
import crypto from "node:crypto";

function verifySlack(rawBody, timestamp, signature, secret, now = Math.floor(Date.now() / 1000)) {
  if (!/^\d{1,12}$/.test(timestamp ?? "") || typeof signature !== "string") return false;
  if (Math.abs(now - Number(timestamp)) > 300) return false;          // five minutes, as Slack's example
  const expected = "v0=" + crypto.createHmac("sha256", secret)
    .update(`v0:${timestamp}:`).update(rawBody).digest("hex");
  const a = Buffer.from(signature), b = Buffer.from(expected);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}
```

```python
import hashlib, hmac, time

def verify_slack(raw_body: bytes, timestamp: str, signature: str, secret: str) -> bool:
    if not timestamp.isdigit() or abs(time.time() - int(timestamp)) > 300:
        return False
    mac = hmac.new(secret.encode(), b"v0:" + timestamp.encode() + b":" + raw_body, hashlib.sha256)
    return hmac.compare_digest(signature.encode(), ("v0=" + mac.hexdigest()).encode())
```

Full handlers with tests in all three languages: [examples/](examples/README.md). Slack's Bolt
frameworks verify for you; the names are in [references/facts.md](references/facts.md).

## Handle the three kinds of request

1. **`url_verification`** when you save the Request URL: answer 200 with the `challenge` value, only
   after the signature checks out. Slack will not save the URL until this succeeds.
2. **`event_callback`**: the event name is `event.type`, the id to deduplicate on is the top-level
   `event_id`. Answer 2xx within three seconds and do the work from a queue.
3. **Interactivity** (a separate Request URL): `application/x-www-form-urlencoded` with one `payload`
   field holding JSON; its `type` says what happened (`block_actions`, `view_submission`, ...).
   The signature is over the form body as sent, not over the decoded JSON.

## Retries and duplicates

- A request not answered with 2xx in three seconds is retried, with `x-slack-retry-num` and
  `x-slack-retry-reason` headers. Treat a retry as a duplicate of an event you may already have:
  deduplicate on `event_id` (see the webhook-idempotency skill).
- To stop Slack retrying one event you answered with an error, send `x-slack-no-retry: 1`.
- Slack disables an app's event subscriptions when most deliveries fail for an hour; the exact rule is
  in [references/facts.md](references/facts.md). Answering fast is what keeps them on.

## Pitfalls

- A global JSON or form body parser running before your route leaves you nothing raw to verify.
- Comparing with `==` leaks timing; use the constant-time compare above.
- The top-level `token` field is deprecated; it is not a substitute for the signature.
- Slack's clock check: a server with a wrong clock refuses every request. Keep NTP on.

## Testing

- Slack's own worked example (a slash command) is one of the test cases in
  `examples/fixtures/vectors.json`; the rest are signed by the openssl
  command line, including a refused url_verification with a bad signature.
- To see exactly what Slack sends, point a capture URL at it first (WebhookVault answers Slack's
  url_verification for its capture URLs), then send the captured request to your own handler with the
  signing secret you test with.

## Using WebhookVault with Slack

What WebhookVault does with Slack requests is in the last section of
[references/facts.md](references/facts.md): the header it checks, where it reads the event name, and
where the capture URL goes in Slack. With an assistant connected to WebhookVault's MCP server, these
skills do the reading:

- A Slack event that never arrived: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-debug-missing-webhook
- A signature verdict that says failed: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-check-verification
- Forwarded Slack events your receiver refused: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-inspect-deliveries

## Related skills

- Wiring a handler into Express, FastAPI or ASP.NET Core: https://github.com/WebhookVault/skills/tree/main/skills/webhook-receiver-patterns
- Deduplicating on `event_id`: https://github.com/WebhookVault/skills/tree/main/skills/webhook-idempotency
- Other signature schemes: https://github.com/WebhookVault/skills/tree/main/skills/webhook-signature-verification
