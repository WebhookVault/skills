# Side effects and other stores

## Contents

- Calls that cannot roll back
- The outbox pattern
- When the handoff to a queue fails
- SQL Server
- Redis
- Testing it

## Calls that cannot roll back

A charge, an email or a call to another company's API happens outside your transaction. If you call
it inside the transaction and the commit then fails, the call happened and the claim did not; the
retry calls it again. If you call it after the commit and crash before it, it never happens.

## The outbox pattern

1. In the claim transaction, also insert a row describing the side effect ("send receipt for order
   ord_1") into an outbox table.
2. Commit. The claim, the business writes and the intent are now durable together.
3. A worker reads the outbox, performs the call, and marks the row done.
4. Give the downstream service an idempotency key derived from the outbox row (many payment and
   messaging APIs accept one), so a worker that crashes after the call and retries it does not
   charge or send twice.

## When the handoff to a queue fails

A receiver that claims the event and then fails to put it on a queue must not leave the claim
committed. Either enqueue inside the same transaction (a jobs table in the same database), or answer
5xx and delete the claim so the sender's retry can try again. A jobs table in the same database is
the simpler of the two.

## SQL Server

A unique index on (source, event_id), then in the transaction:

```sql
INSERT INTO webhook_events (source, event_id) VALUES (@source, @eventId);
```

A duplicate raises error 2627 (unique constraint) or 2601 (unique index): catch it and treat it as
"already handled". Under concurrency the second insert waits for the first transaction's lock on the
key, as in PostgreSQL. Avoid "IF NOT EXISTS (SELECT ...) INSERT ...": without the right locking hints
two sessions can both pass the check.

## Redis

`SET key value NX EX <seconds>` claims a key only if it does not exist, atomically. It is fast, but
it is a separate system from your database: a crash between the Redis claim and the database commit
leaves the event claimed and not processed. Use it to absorb duplicate bursts in front of a database
claim, not instead of one. Set the expiry longer than the sender's redelivery window.

## Testing it

Test against the real database, not a mock: the behaviour that matters (the unique key, the
transaction, the lock under concurrency) lives in the database. The examples in this skill run ten
concurrent copies of one event and assert the handler ran exactly once, and make a handler fail
mid-way and assert nothing was left behind.
