# What a receiver's status code usually means

These are the common meanings in a webhook context. The response body and headers from
`get_delivery` are the evidence; quote them rather than guessing.

| Status | Usual cause | Who fixes it |
|---|---|---|
| 400 | The receiver rejected the body: a schema check, a missing field, a transformation that changed the shape | The receiver, or the action's rules |
| 401, 403 | The receiver wants authentication WebhookVault does not send: a header, a token, an IP allowlist; or its own signature check failed | The action's headers in the app, the receiver's allowlist, or the receiver's verification (WebhookVault signs with `wv-signature` only when the action has a signing secret) |
| 404 | The path is wrong or the route is not deployed | The action's URL, or the receiver's routes |
| 405 | The receiver does not accept this method | The receiver, or the action's method |
| 408, 504 | The receiver or a gateway in front of it timed out | The receiver: acknowledge first, process later |
| 409 | The receiver treats it as a duplicate or a conflict | Usually fine for an idempotent receiver; check the response body |
| 413 | The body is larger than the receiver accepts | The receiver's size limit |
| 415 | The content type is not accepted | The receiver, or a rule that sets `content-type` |
| 422 | The receiver understood the body but refused it | The receiver's business rules; the response body says which |
| 429 | The receiver is rate limiting | The receiver's limits, or the action's own rate limit in the app |
| 500 | The receiver crashed on this request | The receiver; its own logs have the stack |
| 502, 503 | A proxy in front of the receiver had nothing to forward to, or it is down | The receiver's hosting |
| 3xx | The receiver redirects; deliveries do not follow redirects to a new place | Point the action at the final URL |

A 2xx is success whatever the body says. A receiver that answers 200 and then fails internally
looks delivered from here: the evidence is in the receiver's logs.
