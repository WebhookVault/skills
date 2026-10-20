---
name: webhook-event-ordering
description: Handles out-of-order webhooks: compare versions before writing, tombstones for deletes, fetching current state, reconciliation, tested on PostgreSQL. Use when older events overwrite newer data.
license: MIT
metadata:
  author: "webhookvault"
  version: "0.1.0"
  repository: "https://github.com/WebhookVault/skills"
---

# Webhook event ordering

Webhooks do not arrive in the order things happened. A retry of an old event lands after a newer
one; two events sent a millisecond apart race through different servers; a delete can arrive before
the create. A handler that writes "whatever the latest webhook says" will sometimes write old data
over new. Unless a sender explicitly guarantees ordering, assume none.

## Compare before write

Give every stored record the sender's version, and apply an event only when its version is newer:

```sql
INSERT INTO customers (customer_id, email, plan, deleted, version)
VALUES ($1, $2, $3, $4, $5)
ON CONFLICT (customer_id) DO UPDATE
  SET email = EXCLUDED.email, plan = EXCLUDED.plan, deleted = EXCLUDED.deleted, version = EXCLUDED.version
  WHERE customers.version < EXCLUDED.version;
-- 1 row: applied. 0 rows: a newer (or the same) version is already stored, so this event is stale.
```

One statement, so concurrent events cannot interleave between a read and a write: the database
settles on the newest version whatever order they arrive in.

## Where the version comes from

In order of preference; read the sender's documentation for which fields it provides:

1. **A sequence or version number** on the object, incremented on every change.
2. **The object's own update time** in the payload (not the time the webhook was sent), compared
   with a tie-breaker for equal times.
3. **None at all:** do not trust the event's data. Use it as a signal and fetch the current state
   from the sender's API (below).

The webhook's delivery time and your receive time are not versions: retries and races reorder them.

## Deletes leave a tombstone

A delete removes the data but keeps the row, marked deleted, with the delete's version. Otherwise a
late update recreates the record you just deleted, and a delete that arrives before its create is
forgotten when the create lands.

## When in doubt, fetch the current state

For events where order matters and the payload carries no reliable version, treat the webhook as
"something changed on object X" and read X from the sender's API. The API answer is current by
definition. This costs an API call per event and is subject to the sender's rate limits; batch or
debounce when events arrive in bursts.

## Reconcile

Even with all of the above, a sender can lose an event. A periodic job that compares your records
with the sender's API (or the sender's list of recent events) catches what webhooks missed. See
[reconciliation.md](references/reconciliation.md).

## Tested implementations

Compare-before-write with tombstones in Node.js (`pg`), Python (`psycopg` 3) and C# (`Npgsql`),
tested against a real PostgreSQL: in-order events apply; a late older event is stale; a redelivery
of the same version changes nothing; a delete leaves a tombstone a late update cannot resurrect; a
delete arriving before the create still wins; twenty events applied concurrently in random order
settle on the newest. How to run them: [examples/README.md](examples/README.md).

## Related skills

- Duplicates of the same event: https://github.com/WebhookVault/skills/tree/main/skills/webhook-idempotency
- The receiver around this logic: https://github.com/WebhookVault/skills/tree/main/skills/webhook-receiver-patterns
