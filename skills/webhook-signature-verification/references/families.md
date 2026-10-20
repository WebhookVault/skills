# The signature families

## Contents

- HMAC over the body
- Timestamped HMAC in one header
- Timestamped HMAC in two headers
- Standard Webhooks
- URL-bound HMAC
- Public-key signatures
- Shared token
- Choosing a tolerance

The exact signed string matters more than anything else: one byte of difference and nothing
matches. Each family below gives it precisely. The implementations in `examples/` cover every
family, and the sender's own documentation is always the authority for its scheme.

## HMAC over the body

- Signed: the raw body bytes.
- Key: the shared secret as UTF-8 text.
- Algorithm: HMAC-SHA256 (some senders use SHA-1 or SHA-512).
- Encoding: lowercase hex, often with a prefix such as `sha256=`, or base64.
- Replay protection: none. A captured request can be sent again later and still verifies; pair it
  with idempotency on the event id.

GitHub's documentation publishes a test vector for this family: secret `It's a Secret to Everybody`,
body `Hello, World!`, header `sha256=757107ea0eb2509fc211221cce984b8a37570b6d7586c22c46f4379c8b043e17`.

## Timestamped HMAC in one header

- Header: a list such as `t=1700000000,v1=<hex>,v1=<hex>` or `ts=1700000000;h1=<hex>`.
- Signed: the timestamp, a joining character, then the raw body: `<t>.<body>` or `<ts>:<body>`.
- Several signature entries can appear during a secret rotation; accept the request when any one
  matches. Exactly one timestamp entry must appear.
- Check the timestamp against the tolerance before trusting the signature.

## Timestamped HMAC in two headers

- A timestamp header and a signature header such as `v0=<hex>`.
- Signed: `v0:<timestamp>:<body>`, with the version string included.
- Slack's documentation publishes a complete worked example for this family.

## Standard Webhooks

An open specification (https://github.com/standard-webhooks/standard-webhooks) several senders use.

- Headers: `webhook-id`, `webhook-timestamp`, `webhook-signature` (some senders use the same scheme
  with `svix-` header names).
- Secret: `whsec_` followed by base64. The HMAC key is the base64-decoded bytes, not the text.
- Signed: `<id>.<timestamp>.<body>`.
- Signature header: space-separated entries `v1,<base64>`; accept when any `v1` entry matches.
- The specification's library tests publish a vector (all test values):
  secret `whsec_MfKQ9r8GKYqrTwjUPD8ILPZIo2LaLaSw` (test value), id `msg_p5jXN8AQM9LWM0D4loKWxJek`, timestamp `1614265330`, body
  `{"test": 2432232314}`, signature `v1,g0hM9SsE+OTPJTGt/tmIKtSyZlE3uFJELVlNIOLJ1OE=`.

## URL-bound HMAC

- Signed: the full URL the sender called (scheme, host, path and query exactly), then either the
  form fields sorted by name with each name followed by its value, or the raw body. Read which from
  the sender's documentation.
- Often HMAC-SHA1 or HMAC-SHA256, base64.
- The URL must come from configuration: the public URL registered with the sender. A request seen
  behind a proxy carries another scheme, host or port.
- Form values are the decoded values, as the sender sent them, not re-encoded.

## Public-key signatures

- The sender signs with a private key and publishes the public key; there is no shared secret to
  leak. The receiver stores only the public key.
- Ed25519: usually a hex signature over `<timestamp><body>` and a 32-byte public key given as hex.
- ECDSA P-256 with SHA-256: usually a base64 DER signature and a base64 SubjectPublicKeyInfo key.
- Still check the timestamp: a valid signature can be replayed.

## Shared token

- No signature: the sender puts a fixed token in a header. It proves only that the sender knows the
  token, not that the body is unchanged. Compare in constant time, and prefer a signing scheme when
  the sender offers one.

## Choosing a tolerance

Five minutes is the common choice and what several senders' own libraries use. A shorter window
rejects requests from a sender whose retries were delayed; a longer one gives a captured request
more time to be replayed. Whatever the window, deduplicate on the event id as well.
