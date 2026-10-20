---
name: discord-webhooks
description: Receives and verifies Discord Webhook Events and interactions: Ed25519, PING answers, invalid-signature probes, 3 second limit, tested code. Use when building a Discord app endpoint.
license: MIT
metadata:
  author: "webhookvault"
  version: "0.1.0"
  repository: "https://github.com/WebhookVault/skills"
---

# Discord webhooks

Discord pushes to an app over HTTP in two ways, signed the same way with Ed25519:

- **Webhook Events**: app-level events such as `APPLICATION_AUTHORIZED` or `ENTITLEMENT_CREATE`, posted to
  the Events URL on the app's Webhooks page.
- **Interactions endpoint**: slash commands, buttons and modals, posted to the Interactions Endpoint URL;
  your answer is the interaction response.

(Discord's outgoing "webhooks" that post messages into a channel are a different thing and are not covered
here.)

## When to use

- Building or fixing either endpoint for a Discord app.
- Discord will not save the URL, or removed it later.

## Quick facts

<!-- facts:start (generated from data/providers/discord.json by tools/provider-facts.mjs; edit the data, not this block) -->
| | |
|---|---|
| Signature header | X-Signature-Ed25519, with X-Signature-Timestamp |
| Scheme | Ed25519, hex, checked with the application public key |
| Signed content | {timestamp}{raw body}, no separator |
| Where the secret comes from | The application's public key (Developer Portal) |
| Timestamp tolerance | Not stated |
| Event name | event.type (outer type: 0 PING, 1 event) |
| Delivery or event id | Not stated |
| Handshake | PING (type 0): answer 204, empty body, after verifying |
| Expected response | 204, no body |
| Response deadline | 3 seconds |
| Retries | Exponential back-off for up to 10 minutes |

Read from Discord's own pages on 2026-10-20. Every value, its source page and the sentence it came from: [references/facts.md](references/facts.md).
<!-- facts:end -->

## Verify every request before anything else

The signed message is the `X-Signature-Timestamp` value followed by the raw body; the signature is hex in
`X-Signature-Ed25519`; the key is the application's public key (hex) from the Developer Portal.

```js
import crypto from "node:crypto";

const publicKey = crypto.createPublicKey({ format: "jwk", key: {                 // once, at start-up
  kty: "OKP", crv: "Ed25519", x: Buffer.from(process.env.DISCORD_PUBLIC_KEY, "hex").toString("base64url") } });

function verifyDiscord(rawBody, signatureHex, timestamp) {
  if (!/^[0-9a-f]{128}$/i.test(signatureHex ?? "") || typeof timestamp !== "string") return false;
  return crypto.verify(null, Buffer.concat([Buffer.from(timestamp), rawBody]), publicKey, Buffer.from(signatureHex, "hex"));
}
```

Answer 401 to any request that fails. Discord sends invalid signatures on purpose as routine security
checks; an endpoint that accepts one is removed, and a URL whose PING is not verified is never saved. The `discord-interactions` packages
(Node.js, Python) do the same check. Full handlers with tests: [examples/](examples/README.md).

## The PING answers differ

| | Webhook Events | Interactions endpoint |
|---|---|---|
| PING | outer `type` 0 | `type` 1 |
| Answer to PING | 204, empty body | 200 with `{"type": 1}` |
| Answer to the rest | 204, empty body, within 3 seconds | the interaction response, within 3 seconds |
| Event name | `event.type` | `type` (an integer) and `data` |

Answer the PING only after verifying it. Both answers need a valid Content-Type.

## Webhook Events

- Discord retries an unanswered event with back-off for up to 10 minutes, and stops sending if you fail
  too often. Events are neither real time nor ordered.
- Discord documents no delivery id, so make handlers idempotent by state (an entitlement's id and status,
  an authorisation per user).
- Discord states no timestamp window; the examples check none.

## Interactions

- Answer within 3 seconds or the interaction token is invalidated. For slow work, answer with a deferred
  response and follow up with the token, which lasts 15 minutes.

## A capture URL cannot be the Interactions endpoint

Discord saves an Interactions Endpoint URL only after its own signed PING check, which a capture URL does
not answer. Register your own handler there and, if you want a copy of each interaction captured, have the
handler forward it.

## Testing

- The PING sent when you save each URL is Discord's only documented probe.
- `examples/fixtures/vectors.json` is signed by the openssl command line with a key made for that run: both
  PINGs, PINGs with invalid signatures (Discord's check), an event, a command, a changed timestamp.

## Using WebhookVault with Discord

What WebhookVault does with Discord requests is in the last section of
[references/facts.md](references/facts.md): it checks the Ed25519 signature with the public key you paste
and reads the event name from `event.type`. With an assistant connected to WebhookVault's MCP server,
these skills do the reading:

- An event that never arrived: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-debug-missing-webhook
- A signature verdict that says failed: https://github.com/WebhookVault/skills/tree/main/skills/webhookvault-check-verification

## Related skills

- Ed25519 and other schemes in general: https://github.com/WebhookVault/skills/tree/main/skills/webhook-signature-verification
- Wiring a handler into Express, FastAPI or ASP.NET Core: https://github.com/WebhookVault/skills/tree/main/skills/webhook-receiver-patterns
- Posting payload text into Discord channels safely: https://github.com/WebhookVault/skills/tree/main/skills/webhook-hostile-payloads
