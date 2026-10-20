---
name: github-webhooks
description: Receives and verifies GitHub webhooks: X-Hub-Signature-256, ping, delivery ids, 10 second limit, no automatic retries, tested Node.js, Python and C# code. Use when handling GitHub webhooks.
license: MIT
metadata:
  author: "webhookvault"
  version: "0.1.0"
  repository: "https://github.com/WebhookVault/skills"
---

# GitHub webhooks

GitHub posts an event to a repository, organisation or GitHub App webhook when something happens, and,
when the webhook has a secret, signs the body with it in `X-Hub-Signature-256`.

## When to use

- Writing or fixing a handler for repository, organisation or GitHub App webhooks.
- Signatures that never match, or deliveries marked failed in the Recent Deliveries list.
- Missed events after downtime (GitHub does not retry on its own).

## Quick facts

<!-- facts:start (generated from data/providers/github.json by tools/provider-facts.mjs; edit the data, not this block) -->
| | |
|---|---|
| Signature header | X-Hub-Signature-256 (only when a secret is set) |
| Scheme | HMAC-SHA256, hex, prefixed sha256= |
| Signed content | The raw body |
| Where the secret comes from | A secret you choose when creating the webhook |
| Timestamp tolerance | None (no timestamp is signed) |
| Event name | X-GitHub-Event header, plus action in the body |
| Delivery or event id | X-GitHub-Delivery header (a redelivery keeps it) |
| Handshake | ping event when the webhook is created; answer 2xx |
| Expected response | 2xx |
| Response deadline | 10 seconds |
| Retries | None automatic; redeliver by hand within 3 days |

Read from GitHub's own pages on 2026-10-20. Every value, its source page and the sentence it came from: [references/facts.md](references/facts.md).
<!-- facts:end -->

## Set a secret, then verify every request

GitHub sends no signature at all unless the webhook has a secret, so set one (a long random string) and
refuse unsigned requests. Choose content type `application/json`.

```js
import crypto from "node:crypto";

function verifyGitHub(rawBody, header, secret) {
  if (typeof header !== "string" || !header.startsWith("sha256=")) return false;
  const expected = "sha256=" + crypto.createHmac("sha256", secret).update(rawBody).digest("hex");
  const a = Buffer.from(header), b = Buffer.from(expected);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}
```

```python
import hashlib, hmac

def verify_github(raw_body: bytes, header: str, secret: str) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return isinstance(header, str) and hmac.compare_digest(header.encode(), expected.encode())
```

Never accept the older `X-Hub-Signature` (SHA-1). GitHub's own worked example (secret
`It's a Secret to Everybody`, body `Hello, World!`) is one of the test cases; full handlers in three
languages: [examples/](examples/README.md). Octokit's `webhooks.verify` does the same in Node.js.

## Handling an event

- The event name is the `X-GitHub-Event` header; most events also carry an `action` in the body
  (`opened`, `closed`, ...). Check both before acting.
- `ping` arrives once when the webhook is created. Answer 2xx.
- `X-GitHub-Delivery` is a GUID per delivery, and a redelivery keeps it: deduplicate on it.
- The signature covers only the body. The event and delivery headers are not signed and nothing signed
  carries a time, so a captured request can be sent again later. Deduplication on the delivery id stops
  the same delivery counting twice; act on what the body says, not on the header alone.

## Answering, and no retries

- Answer 2xx within 10 seconds; GitHub then cuts the connection and marks the delivery failed. Queue the
  work.
- GitHub does not redeliver failed deliveries automatically. Redeliver from Recent Deliveries or the REST
  API, within 3 days. After an outage, list failed deliveries and redeliver them, or reconcile through the
  API.
- Events over 25 MB are not delivered at all.

## Testing

- The `ping` on creation and the Redeliver button in Recent Deliveries are GitHub's own test tools.
- `examples/fixtures/vectors.json`: GitHub's published example plus requests signed by the openssl command
  line (SHA-1 only, missing prefix, no secret configured, missing event header).
- To see exactly what GitHub sends, add a capture URL as a second webhook, then send the captured request
  to your handler with a test secret.

## Using WebhookVault with GitHub

What WebhookVault does with GitHub requests is in the last section of
[references/facts.md](references/facts.md): it checks `X-Hub-Signature-256` with the secret you paste and
reads the event name from `X-GitHub-Event`. With an assistant connected to WebhookVault's MCP server,
these skills do the reading:

- A delivery that never arrived: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-debug-missing-webhook
- A signature verdict that says failed: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-check-verification
- Forwarded deliveries your receiver refused: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-inspect-deliveries

## Related skills

- Wiring a handler into Express, FastAPI or ASP.NET Core: https://github.com/WebhookVault/skills/tree/main/skills/webhook-receiver-patterns
- Deduplicating on the delivery id: https://github.com/WebhookVault/skills/tree/main/skills/webhook-idempotency
- Other signature schemes: https://github.com/WebhookVault/skills/tree/main/skills/webhook-signature-verification
