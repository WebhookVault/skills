# Choosing the dedupe key

The key must be the same on every delivery of one occurrence and different for different
occurrences. Read the sender's documentation for the field; do not guess from a sample payload.

| Candidate | Use it? |
|---|---|
| The sender's event id (one per occurrence, repeated on retries) | Yes, with the sender's name |
| A delivery, attempt or request id (new on every retry) | No: every retry looks new |
| A message id from a signing scheme (Standard Webhooks `webhook-id`) | Yes, when the sender documents it as stable across retries |
| A forwarder's id for the stored request (WebhookVault's `X-WebhookVault-Request-Id`) | When there is no event id: it is the same on the forwarder's retries and replays, but a sender's own retry arrives as a new request with a new id |
| The object id alone (an order id) | No: an order has many events (created, paid, refunded) |
| The object id plus the event type plus a version or timestamp from the payload | When there is no event id, and the payload carries a version that changes with each change |
| A hash of the raw body | Last resort: it treats two genuinely identical events as one, and some senders change a field (an attempt counter, a sent-at time) on each retry, which defeats it |

## Scope

- **Per sender.** Two senders can both use `evt_1`. Store the sender's name in the key.
- **Per environment.** Test and live events should never share a table, or a test id can block a
  live one.
- **Per handler, when several handlers consume the same event.** If one webhook feeds two
  independent processes, each claims the event under its own name, so one finishing does not stop
  the other.

## Length and type

Store the id as text, not a number, and allow for long ids: some senders use UUIDs, some use long
prefixed strings. Refuse an absurdly long id (hundreds of characters) before it reaches the database.
