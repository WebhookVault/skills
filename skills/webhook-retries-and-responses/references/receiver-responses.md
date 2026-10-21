# Receiver responses in detail

## Speed

- The sender's timeout is usually a few seconds; read its documentation for the exact figure.
- Everything that can wait, waits: calls to other services, emails, heavy database work, file
  processing. Store the event (or put it on a queue) and answer.
- A queue or a jobs table in the same database as the dedupe claim is the simplest durable hand-off.

## Body of the response

- Most senders ignore the response body; some record a short excerpt in their delivery log. Keep it
  small and never put secrets, stack traces or internal paths in it.
- A few senders expect a specific body (a challenge echo during subscription, for example). Those
  rules are sender-specific; follow the sender's documentation exactly.
- A forwarder in front of the receiver may read the body too. A WebhookVault action can require a
  condition on the response (for example `body.status` equals `ok`) or accept specific status
  codes; a 200 whose body misses the condition then counts as a failed delivery and is retried.

## Redirects

Many senders do not follow redirects, and a redirect from `http` to `https` can turn a POST into a
GET in some clients. Give senders the final URL.

## During a deploy or outage

- Answer 503 (optionally with `Retry-After`) rather than closing connections abruptly, so the sender
  treats it as temporary.
- Expect a burst when you come back: senders retry everything that failed. Rate limit fairly, queue,
  and let deduplication absorb the duplicates.

## Status codes to avoid

- 2xx for something you could not store.
- 404 for a temporary routing problem: some senders treat it as permanent.
- 500 for a bad signature: the sender retries a request that can never succeed.
