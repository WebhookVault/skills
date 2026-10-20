# Rule recipes

Each recipe uses paths that are examples only. Replace them with paths that `describe_traffic` shows
the endpoint really receives, then preview on real requests before handing the rule over.

## Only some events reach this action

```json
{
  "version": 1,
  "name": "paid invoices only",
  "when": { "all": [ { "path": "body.type", "op": "equals", "value": "invoice.paid" } ] },
  "steps": []
}
```

A rule that does not match delivers the request unchanged, so a rule alone does not stop other
events. To deliver only matching events, the person puts the same condition on the action itself
in the app.

## Add a header the receiver routes on

```json
{
  "version": 1,
  "name": "tag the source",
  "steps": [ { "op": "set", "path": "headers.X-Source", "value": "payments" } ]
}
```

Never put a secret in a rule: rule documents are readable by every member and by assistants. The
action's signing secret signs deliveries with `wv-signature`.

## Rename and flatten

```json
{
  "version": 1,
  "name": "flatten order",
  "steps": [
    { "op": "rename", "from": "body.data.object.id", "to": "body.orderId" },
    { "op": "rename", "from": "body.data.object.amount", "to": "body.amount" },
    { "op": "keep", "paths": ["body.orderId", "body.amount", "body.type"] }
  ]
}
```

## Remove personal data before a third party sees it

```json
{
  "version": 1,
  "name": "strip contact details",
  "steps": [
    { "op": "remove", "paths": ["body.data.object.customer_email", "body.data.object.customer_phone"] },
    { "op": "redact", "paths": ["body.data.object.billing_address"], "with": "[removed]" }
  ]
}
```

## Amount in cents to a decimal

```json
{
  "version": 1,
  "name": "decimal total",
  "steps": [
    { "op": "compute", "path": "body.total", "fn": "round",
      "args": [ { "fn": "div", "args": ["body.amount_cents", 100] }, 2 ] }
  ]
}
```

If `body.amount_cents` is missing, `body.total` is left as it was; it never becomes 0.

## A summary line for a chat message

```json
{
  "version": 1,
  "name": "summary",
  "steps": [ { "op": "template", "path": "body.summary", "template": "{{body.type}} for {{body.orderId}}" } ]
}
```

Text from a payload is written by the sender's users. When a receiver posts it to a chat channel,
the receiver must escape it for that channel (Slack: `&`, `<`, `>`; Discord: send with no allowed
mentions; Telegram: no parse mode). WebhookVault's own notification actions already do this. See the
`webhook-hostile-payloads` skill:
https://github.com/WebhookVault/skills/tree/main/skills/webhook-hostile-payloads.
