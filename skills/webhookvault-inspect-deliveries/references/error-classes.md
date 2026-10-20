# Delivery error classes

An `Errored` attempt reached no receiver. `get_endpoint_errors` and `get_delivery` name the class
(read from the tool descriptions and the server's classifier on 2026-10-20).

| Class | Meaning | Usual fix |
|---|---|---|
| `timeout` | No answer within the delivery timeout | The receiver answers too slowly: acknowledge first and process in the background |
| `dns` | The host name did not resolve | A typo in the action's URL, or the receiver's DNS record is gone |
| `connection_refused` | The host answered but nothing listens on that port | The receiver is down or listens elsewhere |
| `tls` | The TLS handshake failed | An expired or self-signed certificate, or a host name the certificate does not cover |
| `blocked_target` | WebhookVault refused to connect: the target resolves to a private or reserved address | Deliveries go to public addresses only; point the action at a public URL |
| `http_status` | The receiver answered with a status of 300 or more (redirects are not followed) | See status-codes.md |
| `interrupted` | The attempt was cut short before any outcome was known; it was queued again | Nothing; the retry follows |
| `cancelled` | The send was cancelled while WebhookVault was restarting | Nothing; it is retried |
| `other` | Anything else, with the error text in the attempt | Read the error text |

Many receivers failing with `timeout`, `dns` or `connection_refused` at the same time is unusual;
one receiver failing is that receiver.
