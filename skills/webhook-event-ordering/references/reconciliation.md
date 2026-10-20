# Reconciliation

Webhooks are a fast path, not a ledger. Senders can drop events (an outage longer than their retry
window, a webhook disabled after repeated failures, a bug), and receivers can lose them (a deploy
that answered 2xx before storing). A reconciliation job is how you find out.

## The job

1. On a schedule (hourly or daily, by how much drift you can tolerate), list the objects changed in
   the sender's API since the last run, or the sender's recent events if it offers such a list.
2. For each, compare the sender's version with yours. Apply the newer one through the same
   compare-before-write path the webhooks use, so a webhook and the reconciler can never fight.
3. Record what it fixed. A reconciler that fixes things every run is telling you webhooks are being
   lost: find out why.

## Design notes

- **Use the same write path.** The reconciler is just another source of events with versions.
- **Respect the sender's rate limits.** Page through changes; back off on 429.
- **Overlap the windows.** Start each run a little before the last one ended, so an object changed
  during the previous run is not missed. Compare-before-write makes the overlap harmless.
- **Alert on silence too.** If a stream of webhooks stops entirely, the reconciler sees changes with
  no matching webhooks. That is a signal worth an alert of its own.

## When the sender has no list API

Then webhooks are the only source, and losing one is permanent. Make the receiver as reliable as
possible (store before acknowledging, idempotent, monitored for silence), and capture every request
somewhere you can replay from.
