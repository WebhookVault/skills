---
name: twilio-webhooks
description: Receives and verifies Twilio webhooks: X-Twilio-Signature over the exact URL and parameters, JSON bodySHA256, proxies, retries, tested Node.js, Python and C# code. Use when handling Twilio callbacks.
license: MIT
metadata:
  author: "webhookvault"
  version: "0.1.0"
  repository: "https://github.com/WebhookVault/skills"
---

# Twilio webhooks

Twilio calls your URL when a message or call comes in and when the status of one you sent changes.
Each request is signed with your account's auth token, over the URL Twilio called and the parameters it
sent. Most failures come from the URL, not the token.

## When to use

- Writing or fixing a handler for incoming messages or calls, or for message and call status callbacks.
- Signature checks fail behind a load balancer or proxy, or only on some routes.
- Status callbacks arrive out of order or twice.

## Quick facts

<!-- facts:start (generated from data/providers/twilio.json by tools/provider-facts.mjs; edit the data, not this block) -->
| | |
|---|---|
| Signature header | X-Twilio-Signature |
| Scheme | HMAC-SHA1, base64 |
| Signed content | Full URL + each POST parameter name and value, sorted by name; JSON bodies: URL with bodySHA256 |
| Where the secret comes from | The account's primary Auth Token |
| Timestamp tolerance | None (no timestamp is signed) |
| Event name | Per product; messaging status callbacks: MessageStatus |
| Delivery or event id | No event id; resource SIDs (MessageSid, CallSid); retries carry I-Twilio-Idempotency-Token |
| Handshake | None |
| Expected response | 200 (TwiML where the webhook asks for instructions) |
| Response deadline | 15 seconds total by default (connect 5 seconds) |
| Retries | One retry, on connect or TLS failure only, unless overridden |

Read from Twilio's own pages on 2026-10-20. Every value, its source page and the sentence it came from: [references/facts.md](references/facts.md).
<!-- facts:end -->

## The URL is part of the signature

The signed string starts with the full URL Twilio requested: scheme, host, port, path and query, with
its encoding unchanged. Your server often sees a different one:

- TLS ends at a proxy, so the app sees `http://` while Twilio called `https://`.
- The app sees an internal host or port; rebuild the public URL from configuration, not from the
  request, or from `X-Forwarded-*` headers only when your own proxy sets them.
- A framework adds or removes a trailing slash, or decodes `%2B` in the query.
- Voice callbacks over HTTPS drop the port before signing, SMS callbacks keep it (Twilio's own rule;
  see [references/facts.md](references/facts.md)).

Use the exact URL you configured in Twilio. Never decode or re-encode it.

## Verify, then read

```js
import crypto from "node:crypto";

// Form-encoded body: URL + each name and value, sorted by name, HMAC-SHA1 with the auth token, base64.
function verifyTwilioForm(publicUrl, rawBody, signature, authToken) {
  const fields = [...new URLSearchParams(rawBody.toString("utf8"))]
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
  const signed = publicUrl + fields.map(([k, v]) => k + v).join("");
  const expected = crypto.createHmac("sha1", authToken).update(signed, "utf8").digest("base64");
  const a = Buffer.from(signature ?? ""), b = Buffer.from(expected);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}
```

Use every parameter Twilio sent, not a list you expect: Twilio adds parameters without notice. For a
JSON body Twilio puts `bodySHA256` (hex SHA-256 of the body) in the URL; check it against the body and
sign the URL alone. Twilio's own SDKs have `RequestValidator` (Python, C#) and `validateRequest`
(Node.js); Twilio recommends them, and their names and arguments are in
[references/facts.md](references/facts.md). The examples here implement the same rule so you can see
it and test it: [examples/](examples/README.md), including Twilio's own published example.

## What arrives

- There is no single event type. Status callbacks carry `MessageStatus` (or `CallStatus`) with values
  such as `queued`, `sent`, `delivered`, `undelivered`, `failed`; inbound messages and calls carry the
  message or call fields.
- There is no event id. A message's status changes share one `MessageSid`; deduplicate on
  `MessageSid` plus status, or on `I-Twilio-Idempotency-Token` when a retry carries it.
- Status callbacks are not guaranteed to arrive in order: never let `sent` overwrite `delivered`
  (see the webhook-event-ordering skill).

## Answering

- Informational callbacks need 200. Incoming messages and calls expect TwiML telling Twilio what to do
  (an empty `<Response></Response>` asks for nothing).
- Twilio's default timeouts are short (see the quick facts), and by default it retries once, only when
  it could not connect. A slow handler loses the request: answer fast and queue the work.
- Retries and timeouts can be changed per URL; the parameters are in
  [references/facts.md](references/facts.md).

## Pitfalls

- Middleware that trims whitespace in form fields changes what was signed.
- Twilio will not call an HTTPS URL with a self-signed certificate.
- Twilio publishes no fixed source IP range, so an IP allowlist is not an option; the signature is.

## Testing

- `examples/fixtures/vectors.json` holds Twilio's worked example and
  requests signed by the openssl command line, including the proxy (`http` instead of `https`) and
  trailing-slash failures above.
- To see exactly what Twilio sends, set a capture URL as the callback first, then send the captured
  request to your handler with the URL and test auth token you sign with.

## Using WebhookVault with Twilio

What WebhookVault does with Twilio requests is in the last section of
[references/facts.md](references/facts.md): it checks the signature with your auth token against the
capture URL, and lists requests without an event name. With an assistant connected to WebhookVault's
MCP server, these skills do the reading:

- A callback that never arrived: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-debug-missing-webhook
- A signature verdict that says failed: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-check-verification
- Forwarded callbacks your receiver refused: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-inspect-deliveries

## Related skills

- Wiring a handler into Express, FastAPI or ASP.NET Core: https://github.com/WebhookVault/skills/tree/main/skills/webhook-receiver-patterns
- Out-of-order status callbacks: https://github.com/WebhookVault/skills/tree/main/skills/webhook-event-ordering
- Other signature schemes: https://github.com/WebhookVault/skills/tree/main/skills/webhook-signature-verification
