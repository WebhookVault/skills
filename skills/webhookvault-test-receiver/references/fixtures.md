# Turning a captured request into a test fixture

A real captured request is the best test input for a receiver: it has the exact shape, encoding
and headers the sender uses.

1. Read it with `get_request(endpointId, requestId)`. For a large body, read the chunks with
   `bodyOffset` until there is no `nextOffset`.
2. Save the body exactly as returned, byte for byte, as a file in the person's test folder (for
   example `tests/fixtures/<provider>-<event>.json`). Do not reformat or re-serialise JSON: the
   signature, if the test checks one, covers the exact bytes.
3. Save the headers the receiver reads (event name, delivery id, content type) beside it. Leave
   credential headers out; they read `[redacted]` anyway.
4. Remove personal data before committing a fixture: names, emails, addresses and phone numbers in
   the body. Card numbers are already masked by WebhookVault.
5. To test signature checking, sign the saved body with a test secret in the test itself, not with
   the real signing secret. The `webhook-signature-verification` skill shows how per scheme:
   https://github.com/WebhookVault/skills/tree/main/skills/webhook-signature-verification.

To try the stored request against a receiver on the person's own machine, the request's **curl**
button in the app copies a curl command with the stored method, headers and body, addressed to the
capture URL. The person replaces that URL with their receiver's local address and runs it. The
button is not offered for a body that was cut at the plan's size cap.
