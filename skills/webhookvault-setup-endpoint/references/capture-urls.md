# Capture URLs

A capture URL has the form `https://in.webhookvault.net/hook/<endpoint id>`. Anything a sender adds
after the id (a sub-path, a query string) is kept with the request.

- **Public by design.** Senders must be able to reach it without logging in, so anyone who knows it
  can send to it. Share it only with the sender. Do not post it in public issues, chats, screenshots
  or front-end code.
- **Verification is the proof.** With the provider's signing secret set, every request carries a
  verdict: `verified` requests came from the holder of the secret. Treat unsigned or failed requests
  as untrusted, whoever they claim to be from.
- **A leaked URL.** A person can create a new endpoint and move the sender to it, then switch the old
  one off. Requests sent to an endpoint that is off are refused with 410 and not stored.
- **HTTP and HTTPS.** Senders should use `https://`. The capture host answers both so that a sender
  configured with `http://` is not bounced mid-request, but the request then travels unencrypted.
- **Answering the sender.** By default WebhookVault answers 200 as soon as the request is stored. A
  person can set a custom response on the endpoint for senders that expect a particular body.
