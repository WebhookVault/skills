# Verification notes and what they mean

Read from the server's verifier on 2026-10-20. `<header>` stands for the provider's signature header
(for example `Stripe-Signature`).

## failed

| Note | Cause |
|---|---|
| "`<header>` does not match the HMAC-... of the body with the configured secret." | The wrong secret, a rotated secret, or a body changed on the way (a proxy that re-encodes JSON) |
| "`<header>` does not match the HMAC over ..." | The same, for schemes that sign a timestamp or URL with the body |
| "`<header>` does not verify ... with the stored public key ..." | The wrong public key for a key-pair scheme (Ed25519, ECDSA), or a key from another app |
| "`<header>` does not equal the configured secret." | A shared-secret scheme (a token in a header) with the wrong token |
| "The signature timestamp is ... from the capture time, outside the ... tolerance." | A late re-send by the provider, or a sender clock far off |
| "`<header>` carries no v1 signature." or "... no usable signature value." | A malformed header, or a different scheme version than configured |
| "`<header>` carries no `<key>`= timestamp." / "... is missing." | A header the scheme needs is absent: often a different sender or a proxy that strips headers |
| "`<header>` is not base64." / "The signature could not be decoded" | A malformed signature, or the wrong scheme for this sender |

## unsigned

| Note | Cause |
|---|---|
| "No `<header>` header on the request." | The sender did not sign this request: a test button that does not sign, another sender, or signing switched off at the provider |
| "The payload has no signature object ..." | A scheme that signs inside the body found no signature there |

## unverifiable

| Note | Cause |
|---|---|
| "No signing secret is configured." | Set the secret on the endpoint |
| "`<scheme>`: not verified ... yet." | A scheme WebhookVault does not check; the receiver must verify |
| "The body exceeded the capture limit, so the signed content is not available." | The body was over the plan's capture cap |
| "The public capture URL is unknown, and this scheme signs it." | A URL-bound scheme; WebhookVault could not rebuild the signed URL |
| "The secret is not a valid whsec_ base64 key." | A Standard Webhooks secret pasted incompletely |
| "The stored public key is not ..." | A key-pair scheme with a malformed public key |

Timestamps are compared with the time WebhookVault captured the request, not the time of the check,
so re-verifying stored history later does not make old requests fail on age.
