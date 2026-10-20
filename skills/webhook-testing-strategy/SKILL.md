---
name: webhook-testing-strategy
description: Tests webhook integrations without guesswork: real captured samples as fixtures, signed test requests, duplicate, out-of-order and failure cases, provider test modes. Use when planning receiver tests.
license: MIT
metadata:
  author: "webhookvault"
  version: "0.1.0"
  repository: "https://github.com/WebhookVault/skills"
---

# Webhook testing strategy

Webhook bugs hide in the gap between what the documentation says a sender sends and what it really
sends, and in the cases that only happen in production: the retry, the duplicate, the event that
arrives before the one it depends on. Test against real shapes and make those cases routine.

## Three layers

1. **Unit tests with fixtures.** The handler's logic, fed real captured payloads stored as files.
   Fast, no network, run on every change.
2. **Integration tests with signed requests.** The whole receiver over HTTP: raw body, signature
   check, dedupe, status codes. Sign each request in the test with a test secret.
3. **End to end through the real sender.** A provider's test mode or "send test event" button,
   pointed at a capture URL or a staging receiver, to confirm the URL, the subscription and the secret.

## Fixtures from real requests

- Capture real requests from the sender (test mode is enough) and store the bodies as fixtures, one
  per event type you handle. Keep the bytes exactly as received when a test checks a signature over
  them; otherwise scrub them.
- Scrub personal data before committing: [scripts/scrub_fixture.py](scripts/scrub_fixture.py)
  replaces emails, phone numbers and long digit runs and keeps everything else. Read the output: it
  does not detect names or addresses.
- Name fixtures by sender and event (`shop-order-created.json`) and record when they were captured.
  Senders add fields; refresh fixtures when you upgrade a sender's API version.
- WebhookVault is one way to capture real requests with their exact headers and bytes; any capture
  tool or the sender's delivery log works too.

More: [fixtures.md](references/fixtures.md).

## Signed test requests

Sign fixtures inside the test with a test secret, using the same scheme as the sender. Never put a
real signing secret in a test or a fixture. The `webhook-signature-verification` skill has signing
code for every common scheme and a script that prints the headers for a body:
https://github.com/WebhookVault/skills/tree/main/skills/webhook-signature-verification

## The cases that matter

Every receiver test suite covers these, not only the happy path:

| Case | Expect |
|---|---|
| Valid signed event | Processed once, 2xx |
| Same event again | 2xx, not processed again |
| Wrong secret, tampered body, stale timestamp, missing header | 401, nothing changes |
| Body re-serialised (spaces, key order) | 401: the signature is over the bytes |
| Older event after a newer one | Newer state kept |
| Delete before create | Deleted state kept |
| Downstream failure during processing | 5xx, and the retry succeeds |
| Oversized body | 413 |
| Malformed JSON with a valid signature | 400 |
| Payload text with markup or instructions | Shown escaped, never acted on |

Details and how to build each: [negative-cases.md](references/negative-cases.md).

## A receiver on your own machine

Run the receiver locally and send it signed fixtures from the test or with curl. Capture services and
providers deliver to public URLs; to try a captured request against a local receiver, take the stored
method, headers and body and send them yourself.

## Related skills

- Tested receiver skeletons to start from: https://github.com/WebhookVault/skills/tree/main/skills/webhook-receiver-patterns
- Duplicates: https://github.com/WebhookVault/skills/tree/main/skills/webhook-idempotency
- Ordering: https://github.com/WebhookVault/skills/tree/main/skills/webhook-event-ordering
