# How WebhookVault retries a delivery

Read from https://docs.webhookvault.net/documentation/concepts and
https://docs.webhookvault.net/documentation/deliveries on 2026-10-20.

- A forward is attempted **eight times in all**. The first retry waits about 30 seconds after the
  first failure and each later wait doubles, so the retries span about an hour.
- When the last attempt fails, the delivery is parked as `DeadLetter`. Nothing more is sent until a
  replay, which starts it fresh.
- Every attempt, automatic or manual, is recorded with what was sent and what came back.
- Switching an endpoint off stops its deliveries at once, including retries that were waiting and
  replays already queued: they are cancelled with that reason in the history, not sent later.
  Switching it back on does not resend them; replay the requests that should be delivered.
- Bodies are stored up to 256 KB each way and marked as cut when larger; the full body still went
  over the wire.

## What this means for a fix

- A receiver fixed within the hour usually catches the remaining retries on its own: check
  `list_deliveries` before suggesting any replay.
- A receiver fixed after the retries ran out leaves dead letters: replay those, with the person's
  agreement, one request at a time or as the person directs.
- Do not describe the retry window as longer than about an hour.
