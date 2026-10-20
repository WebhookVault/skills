# Dead letters

A dead letter is a delivery that used up its retry budget. It is not a failure to hide; it is the
point where a person takes over.

## What to keep

- The original request: method, headers (credentials redacted), body, and when it was first sent.
- Every attempt: when, the status or network error, how long it took, a short excerpt of the answer.
- Why it stopped: the attempt budget, the time budget, or a permanent 4xx.

## What to do

1. **Alert once per incident**, not once per dead letter: a receiver that is down produces hundreds.
2. **Fix the receiver**, or the URL or credentials that made it fail.
3. **Replay** the dead letters, oldest first, through the same delivery path, so the same signing,
   transformation and idempotency rules apply. Replays are safe only if the receiver deduplicates.
4. **Keep the history** of the replay beside the original attempts.

## What not to do

- Retry dead letters automatically forever: that is a longer retry budget with no one watching.
- Delete them silently after a while: a person must decide.
- Replay a permanent rejection (400, 422) unchanged: it will be rejected again. Fix the payload or the
  receiver first.
