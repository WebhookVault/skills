---
name: webhook-receiver-patterns
description: Structures a webhook receiver: size cap, raw body, verify, deduplicate, acknowledge, process later, with tested Express, FastAPI and ASP.NET Core skeletons. Use when building or reviewing a receiver.
license: MIT
metadata:
  author: "webhookvault"
  version: "0.1.0"
  repository: "https://github.com/WebhookVault/skills"
---

# Webhook receiver patterns

A webhook receiver is a public endpoint that anyone can call, that a sender will call again when it
is slow or fails, and whose caller gives up after a few seconds. Most receiver bugs come from doing
the right steps in the wrong order. This is the order.

## The handler sequence

1. **Cap the size** before reading the whole body. Refuse with `413`. Count bytes while reading; a
   `Content-Length` header can lie.
2. **Read the raw bytes.** Never let the framework parse the body first: the signature covers the
   bytes as sent.
3. **Verify the signature** from those bytes. Refuse with `401`. Nothing before this point may change
   state: an unverified request must not use up an event id, write a row or wake a job.
4. **Parse** the same bytes. A verified body that does not parse is `400`.
5. **Deduplicate** on the sender's event id. Senders retry; the same event arrives more than once.
   A duplicate is acknowledged with `2xx` and not processed again.
6. **Hand off and acknowledge.** Put the event on a queue (or a jobs table) and answer `2xx`
   quickly. The sender is waiting with a short timeout; slow work belongs after the response.
7. **If the hand-off fails, answer `5xx`** so the sender retries, and make sure the event id is not
   left marked as handled.

```js
app.post("/webhooks", express.raw({ type: () => true, limit: 256 * 1024 }), async (req, res) => {
  if (!verify(req.body, req.get("Webhook-Signature"), secret)) return res.status(401).end();
  let event;
  try { event = JSON.parse(req.body.toString("utf8")); } catch { return res.status(400).end(); }
  if (!(await store.firstTime(event.id))) return res.status(200).json({ duplicate: true });
  try { await queue.enqueue(event); } catch { return res.status(500).end(); }
  res.status(200).json({ received: true });
});
```

## Tested skeletons

The same receiver in three frameworks, each driven over HTTP by tests that sign requests with the
openssl command line and check every step above: a signed event is queued once, a duplicate is
acknowledged and not queued again, a bad or stale signature is `401` and uses up nothing, a
non-JSON or id-less body is `400`, an oversized body is `413`, a failed hand-off is `500`, and
re-formatted JSON fails verification. How to run them: [examples/README.md](examples/README.md).

- Express 5: `examples/node/app.mjs`
- FastAPI: `examples/python/app.py`
- ASP.NET Core minimal API: `examples/csharp/WebhookReceiver.cs`

## Choices that matter

- **Status codes.** `2xx` means "I have it, stop sending". Use `401` for a failed signature, `400`
  for a malformed verified body, `413` for too large, `5xx` only when a retry could succeed. Some
  senders treat any `4xx` as permanent; read the sender's documentation before returning one for a
  temporary problem. More in the `webhook-retries-and-responses` skill:
  https://github.com/WebhookVault/skills/tree/main/skills/webhook-retries-and-responses
- **The dedupe store** must survive restarts and be shared by every instance: a database table with
  a unique key on the event id, written before the work starts. The in-memory store in the examples
  is for the examples only. How, with races and partial failure: the `webhook-idempotency` skill,
  https://github.com/WebhookVault/skills/tree/main/skills/webhook-idempotency
- **One route, one parser.** Give the webhook route its own raw-body handling; a global JSON parser
  registered first consumes the body. Per framework: [frameworks.md](references/frameworks.md).

## Before shipping

Run the review list in [checklist.md](references/checklist.md): secrets, logging, limits, health,
monitoring, and what happens on deploy.

## Related skills

- Every signature scheme, with tested code: https://github.com/WebhookVault/skills/tree/main/skills/webhook-signature-verification
- Treating payload text as hostile: https://github.com/WebhookVault/skills/tree/main/skills/webhook-hostile-payloads
