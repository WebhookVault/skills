# Receiver review checklist

## Secrets

- The signing secret comes from the environment or a secret store, never the code or a committed
  config file.
- Test and live environments have different secrets, and each receiver reads the right one.
- Rotation is planned: the receiver can hold two secrets during a change-over.

## Order of work

- Size cap, raw bytes, verify, parse, deduplicate, hand off, acknowledge: in that order.
- Nothing changes state before the signature is verified.
- A failed hand-off answers 5xx and leaves the event id free to be retried.

## Responses

- 2xx only when the event is safely stored or queued.
- 401 for a bad signature, 400 for a malformed verified body, 413 for too large.
- No stack traces, internal paths or secrets in any response body.
- The response comes back well within the sender's timeout; slow work happens after.

## Logging

- Log the event id, type, outcome and timing.
- Never log the signing secret, the full signature header, authorization headers or tokens.
- Payload text is written by the sender's users: escape it before it reaches a log viewer, a chat
  message or an HTML page.

## Limits and capacity

- A body size cap at the receiver, and the same or larger at any proxy in front.
- A rate or concurrency limit that cannot be exhausted by one noisy sender.
- The queue absorbs a burst: senders replay a backlog all at once after an outage.

## Operations

- A health check that does not need a signed request.
- Monitoring for "nothing arrived" as well as for errors: a sender that stops sending raises no error.
- A deploy does not drop requests in flight; the sender retries what failed, and duplicates are
  handled.
- A way to replay a stored event to the receiver after a fix.
