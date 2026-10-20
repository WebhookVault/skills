---
name: webhook-signature-verification
description: Verifies webhook signatures correctly in Node.js, Python and C#: raw bodies, HMAC, timestamps, Standard Webhooks, URL-bound and public-key schemes. Use when writing or debugging a signature check.
license: MIT
metadata:
  author: "webhookvault"
  version: "0.1.0"
  repository: "https://github.com/WebhookVault/skills"
---

# Webhook signature verification

Anyone who finds a webhook URL can send to it. A signature proves the request came from the holder
of a secret (or a private key) and that nobody changed it on the way. Every sender signs a little
differently, but the schemes fall into a few families, and the same few mistakes break all of them.

## Pick the family

Read the sender's documentation for three things: which header carries the signature, what exactly
is signed, and how the result is encoded. Then match it here.

| Family | What is signed | Typical header shape |
|---|---|---|
| HMAC over the body | The raw body bytes | `sha256=<hex>` or `<base64>` |
| Timestamped HMAC, one header | A timestamp and the body, such as `<t>.<body>` | `t=<unix>,v1=<hex>` |
| Timestamped HMAC, two headers | `v0:<timestamp>:<body>` | signature `v0=<hex>`, timestamp separate |
| Standard Webhooks | `<id>.<timestamp>.<body>`, key from a `whsec_` secret | `v1,<base64>` (space-separated list) |
| URL-bound HMAC | The full URL the sender called, plus form fields or the body | `<base64>` |
| Public key (Ed25519, ECDSA) | A timestamp and the body, signed with the sender's private key | `<hex>` or `<base64>` |
| Shared token | Nothing: a fixed token in a header | the token |

Each family in detail, with the exact signed string: [families.md](references/families.md).

## The five ways it goes wrong

1. **The framework parsed the body first.** Every scheme signs the bytes as sent. Parsing JSON and
   serialising it again changes whitespace, key order or number formatting, and nothing matches.
   Read the raw bytes, verify, then parse. Per framework: [frameworks.md](references/frameworks.md).
2. **The URL is not the URL the sender called.** URL-bound schemes sign the public address. Behind a
   proxy or load balancer the app sees another scheme, host or port. Use the URL from configuration.
3. **The secret is in the wrong form.** Some secrets are used as text, some are base64 key bytes
   after a prefix (Standard Webhooks), and public-key schemes have no secret at all. Test and live
   environments have different secrets.
4. **Comparing with `==`.** A plain comparison stops at the first different character and leaks how
   much of a guess was right. Compare in constant time, after checking lengths.
5. **Accepting any timestamp.** A timestamped signature protects against replays only if the
   timestamp is checked. Reject anything outside a tolerance, commonly five minutes, and keep the
   server clock synced.

## The core, in Node.js

```js
import crypto from "node:crypto";

function verifyHmacBody(rawBody, signatureHeader, secret) {
  const expected = "sha256=" + crypto.createHmac("sha256", secret).update(rawBody).digest("hex");
  const a = Buffer.from(String(signatureHeader ?? ""));
  const b = Buffer.from(expected);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

// Express: give the webhook route the raw body, verify, then parse.
app.post("/webhooks", express.raw({ type: "*/*" }), (req, res) => {
  if (!verifyHmacBody(req.body, req.get("X-Signature"), process.env.WEBHOOK_SECRET)) return res.sendStatus(401);
  const event = JSON.parse(req.body.toString("utf8"));
  res.sendStatus(200); // acknowledge, then process
});
```

## Tested implementations

Every family in three languages, each checked against signatures made by the openssl command line,
against the examples GitHub, Slack and the Standard Webhooks specification publish, and against the
failure cases (a changed byte, the wrong secret, a stale timestamp, a re-serialised body, a missing
or malformed header):

- Node.js, no dependencies: `examples/node/verify.mjs`
- Python, standard library plus `cryptography` for the key-pair schemes: `examples/python/verify.py`
- C#, .NET 9 or later, plus BouncyCastle for Ed25519: `examples/csharp/WebhookSignatures.cs`

How they are tested and how to run them: [examples/README.md](examples/README.md).

To feed a receiver a correctly signed test request, [scripts/sign_request.py](scripts/sign_request.py)
signs a body with a test secret from an environment variable.

## Debugging a mismatch

Log the lengths and the algorithm, never the secret or the full signature: the body length you
hashed against the `Content-Length` received, the signed string's prefix (`t=...` and the first
bytes), and which secret you used (by name). The usual causes, in order: a parsed body, the wrong
secret or environment, a proxy that changed the URL or re-encoded the body, a stale timestamp.
Rotating secrets without downtime: [rotation.md](references/rotation.md).

## Related skills

- Duplicates and retries after verification: https://github.com/WebhookVault/skills/tree/main/skills/webhook-idempotency
- The handler sequence around the check: https://github.com/WebhookVault/skills/tree/main/skills/webhook-receiver-patterns
