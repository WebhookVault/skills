---
name: webhook-idempotency
description: Makes webhook handlers safe to run twice: the dedupe key, an insert-first claim in one transaction, concurrent duplicates and partial failure, tested on PostgreSQL. Use when duplicates cause harm.
license: MIT
metadata:
  author: "webhookvault"
  version: "0.1.0"
  repository: "https://github.com/WebhookVault/skills"
---

# Webhook idempotency

Every webhook will arrive more than once sooner or later. Senders retry after a timeout even when
the first attempt worked; networks resend; people replay events by hand; a receiver crashes after
doing the work and before answering. A handler that charges, ships or emails must produce the same
result however many times an event arrives.

## Choose the key

Deduplicate on the sender's **event id**: the identifier of the occurrence, which stays the same on
every retry. Store it with the **sender's name**, because ids are unique only per sender. Read the
sender's documentation for which field that is; a delivery or attempt id changes on each retry and
is the wrong key. When a sender has no event id, see [choosing-the-key.md](references/choosing-the-key.md).

## Claim first, in the same transaction

The pattern that holds under retries, crashes and two copies arriving in the same millisecond:

1. Begin a transaction.
2. `INSERT` the (sender, event id) into a table whose primary key is exactly that pair. If the
   insert conflicts, the event was handled: stop and acknowledge.
3. Do the business writes in the same transaction.
4. Commit.

```sql
CREATE TABLE webhook_events (
  source text NOT NULL, event_id text NOT NULL, received_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (source, event_id)
);
-- in the handler's transaction:
INSERT INTO webhook_events (source, event_id) VALUES ($1, $2) ON CONFLICT DO NOTHING;
-- 0 rows: a duplicate, stop. 1 row: do the work, then COMMIT.
```

Why each part matters:

- **The unique key, not a lookup.** "Check whether it exists, then insert" lets two concurrent
  copies both see nothing and both run. The key makes the second insert wait for the first
  transaction and then conflict.
- **The same transaction.** If the claim commits first and the work fails, the event is marked
  handled and never processed. If the work commits first and the claim fails, it runs twice. In one
  transaction a failure rolls back both, and the sender's retry processes the event cleanly.
- **After verifying the signature.** Claim only verified events, or anyone can use up your ids.

## Tested implementations

The claim with Node.js (`pg`), Python (`psycopg` 3) and C# (`Npgsql`), each tested against a real
PostgreSQL: a redelivery is a duplicate; the same id from two senders is two events; a failed
handler leaves no claim and no business row, and the retry succeeds; ten copies arriving at once run
the handler exactly once; old claims can be deleted. How to run them:
[examples/README.md](examples/README.md).

- Node.js: `examples/node/once.mjs`
- Python: `examples/python/once.py`
- C#: `examples/csharp/ProcessOnce.cs`

## Side effects outside the database

A call to a payment API or an email service cannot roll back with your transaction. Record the
intent in the same transaction and perform it afterwards from an outbox, passing your own
idempotency key to the downstream service where it accepts one. Details and other stores (SQL Server,
Redis): [side-effects.md](references/side-effects.md).

## Keeping the table small

Delete claims older than the longest time a sender could still redeliver (its retry window plus any
manual replay you allow), with a margin. Thirty days is a common choice. Run it as a scheduled job.

## Related skills

- Where the claim sits in the handler sequence: https://github.com/WebhookVault/skills/tree/main/skills/webhook-receiver-patterns
- Old events arriving after newer ones: https://github.com/WebhookVault/skills/tree/main/skills/webhook-event-ordering
