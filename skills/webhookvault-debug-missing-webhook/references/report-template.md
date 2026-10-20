# Report template

Finish every investigation with a short report in this shape, so the person can act on it and
forward it to whoever owns the sender or the receiver.

```
Endpoint: <name> (<endpointId>)
Window searched: <since> to <until>
What arrived: <none / n requests; the matching request id(s)>
Verification: <verified / failed with note / unsigned / unverifiable / not checked>
Delivery: <not attempted / Succeeded / Failed with status / Errored with error class / DeadLetter>
Where it stopped: <before WebhookVault / at WebhookVault / between WebhookVault and the receiver / inside the receiver>
Cause: <one sentence, with the evidence that shows it>
Evidence: <request ids, attempt ids, finding codes>
Next step: <what to do> (who: <the person in the app / the sender's settings / the receiver's code>)
Replayed: <no / yes: request id, when, with the person's agreement>
Monitoring: <watchdog state, and whether an alarm would reach anyone>
```

Keep untrusted text out of the summary lines except as short quotes, marked as quoted from the
request or response.
