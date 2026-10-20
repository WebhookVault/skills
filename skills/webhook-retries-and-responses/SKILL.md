---
name: webhook-retries-and-responses
description: Chooses receiver status codes and timing, and retries deliveries well: fast acks, which codes retry, backoff with jitter, Retry-After, dead letters. Use when webhooks retry, time out or get lost.
license: MIT
metadata:
  author: "webhookvault"
  version: "0.1.0"
  repository: "https://github.com/WebhookVault/skills"
---

# Webhook retries and responses

A webhook is a conversation with two clocks: the sender waits a few seconds for an answer, then
decides whether to try again. The receiver's status code and speed decide what happens next; the
sender's retry policy decides how much pressure a failing receiver gets. This skill covers both
sides.

## As the receiver: answer fast and honestly

1. **Acknowledge quickly.** Verify, deduplicate, store or queue, answer. Do the slow work after the
   response. Many senders give up after a few seconds and retry; a slow 200 can arrive as a
   duplicate.
2. **Choose the status for what the sender should do next:**

| Answer | Means to the sender | Use for |
|---|---|---|
| 2xx | Stop, it is handled | Stored or queued (including a duplicate you already have) |
| 401 or 403 | Do not retry the same request | Failed signature |
| 400 or 422 | Do not retry the same request | A verified body you cannot accept |
| 410 | This endpoint is gone; some senders disable the webhook | Only when you want deliveries to stop |
| 429 | Slow down, retry later (with `Retry-After`) | Your own rate limit |
| 5xx | Try again later | A temporary failure: database down, queue unavailable |

3. **Never answer 2xx for something you dropped.** The sender will not resend it.
4. **Read the sender's documentation** for how it treats each code and how long it keeps retrying;
   senders differ, and some disable a webhook after repeated failures. The provider skills record
   each sender's documented behaviour with the date it was read.

More detail: [receiver-responses.md](references/receiver-responses.md).

## As the sender: retry without making things worse

When you deliver webhooks, or call another service from a webhook handler:

- **Retry only what can succeed later:** network errors, timeouts, 408, 425, 429 and 5xx. Every
  other 4xx is a permanent answer; retrying it wastes both sides' resources.
- **Exponential backoff with full jitter:** wait a random time between zero and
  `min(cap, base * 2^attempt)`. The doubling backs off from a struggling receiver; the jitter keeps
  many senders from retrying in lockstep after an outage.
- **Honour `Retry-After`** (seconds or an HTTP date, RFC 9110) when the receiver sends one, and stop
  rather than ignore it when it asks for longer than your budget allows.
- **Set a budget** in attempts and in total time, then park the delivery as a **dead letter** that a
  person can inspect and replay. Never retry forever.
- **Make every delivery idempotent on the receiving side** by sending a stable event id, so a retry
  of something that did succeed is harmless.

```js
function backoffDelay(attempt, baseMs = 1000, capMs = 900_000) {
  return Math.floor(Math.random() * Math.min(capMs, baseMs * 2 ** attempt)); // full jitter
}
const retryable = (s) => s === 408 || s === 425 || s === 429 || (s >= 500 && s <= 599);
```

## Tested implementations

Status classification, backoff with full jitter, `Retry-After` parsing (checked against RFC 9110's
own example date) and a delivery loop with attempt and time budgets ending in a dead letter, in
Node.js, Python and C#, with randomness, the clock and sleep injected so every test is exact. How to
run them: [examples/README.md](examples/README.md).

## Dead letters

A dead letter is a delivery that used up its budget. Keep the request, the attempts and the last
answer; alert a person; let them replay it once the receiver is fixed. A replay goes through the
same idempotency check, so replaying something that did arrive is safe. See
[dead-letters.md](references/dead-letters.md).

## Related skills

- The receiver's handler sequence: https://github.com/WebhookVault/skills/tree/main/skills/webhook-receiver-patterns
- Making duplicates harmless: https://github.com/WebhookVault/skills/tree/main/skills/webhook-idempotency
