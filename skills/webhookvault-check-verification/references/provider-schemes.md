# Signature scheme families

For one provider's exact header, scheme, secret label and console path, call
`list_providers(slug)`: it answers from WebhookVault's own catalogue, which is what the verifier
uses. This page explains the families so a failure note makes sense.

| Family | What is signed | What breaks it |
|---|---|---|
| Raw body HMAC | The exact body bytes, with the shared secret (hex or base64 digest in a header) | The wrong secret; any change to the body bytes on the way |
| Timestamped HMAC | A timestamp and the body, often as `timestamp.body`; the header carries both | The above, plus a timestamp outside the tolerance |
| Standard Webhooks | The message id, timestamp and body, with a `whsec_` secret | A secret pasted without its `whsec_` prefix or cut short; missing id or timestamp headers |
| URL-bound HMAC | The full URL the sender called, sometimes with the form fields | The URL configured at the sender differs from the capture URL (a different host, path or query) |
| Public-key signature | A timestamp and body, signed with the sender's private key; verified with its public key (Ed25519, ECDSA) | The wrong public key, often from another app or environment |
| Shared secret | No signature: a fixed token in a header | The wrong token |
| Signed in the body | A signature object inside the JSON payload | A body that is not JSON, or no signature object |

Some providers use a scheme WebhookVault does not check yet (for example a certificate chain fetched
from the provider). Their captures read `unverifiable` with the scheme named; the receiver verifies
them, usually with the provider's own SDK or verification API.
