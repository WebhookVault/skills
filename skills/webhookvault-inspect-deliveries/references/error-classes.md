# Delivery error classes

`get_endpoint_errors` and `get_delivery` name the class of every failed attempt (read from the
tool descriptions and the documentation, October 2026). Most classes mean an `Errored` attempt that
reached no receiver; `http_status` and `response_check` mean the receiver answered, and the
attempt reads `Failed`.

| Class | Meaning | Usual fix |
|---|---|---|
| `timeout` | No answer within the delivery timeout | The receiver answers too slowly: acknowledge first and process in the background |
| `dns` | The host name did not resolve | A typo in the action's URL, or the receiver's DNS record is gone |
| `connection_refused` | The host answered but nothing listens on that port | The receiver is down or listens elsewhere |
| `tls` | The TLS handshake failed | An expired or self-signed certificate, or a host name the certificate does not cover |
| `blocked_target` | WebhookVault refused to connect: the target resolves to a private or reserved address | Deliveries go to public addresses only; point the action at a public URL |
| `http_status` | The receiver answered with a status of 300 or more (redirects are not followed). A code the action lists as accepted, such as `409`, counts as delivered instead | See status-codes.md |
| `response_check` | The receiver answered, but not the way the action's success check expects, for example a 200 whose body reports an error | Read the attempt's error ("Response check failed: ..."): fix the receiver's answer, or a person corrects the check in the app |
| `interrupted` | The attempt was cut short before any outcome was known; it was queued again | Nothing; the retry follows |
| `cancelled` | The send was cancelled while WebhookVault was restarting | Nothing; it is retried |
| `other` | Anything else, with the error text in the attempt | Read the error text |

A failed response check is retried on the normal schedule and parked as a dead letter when the
retries run out, like any other failure. When nothing came back (a timeout, a refused
connection), there was nothing to check: the attempt fails for that reason and its `responseCheck`
reads `skipped`. A check that reads the JSON body fails on a response that is not JSON, is empty
or was larger than the part kept for checking, and says so in the error.

Many receivers failing with `timeout`, `dns` or `connection_refused` at the same time is unusual;
one receiver failing is that receiver.
