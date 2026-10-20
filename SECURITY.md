# Security

These skills tell AI assistants how to handle webhooks, and some of them tell an assistant how to
use the WebhookVault MCP server, which can replay stored requests to live receivers. A wrong
instruction here can do real harm, so reports are taken seriously.

## What to report

- A skill that tells an assistant to follow text found inside a webhook payload, header or
  response, or that fails to warn against it.
- A skill that asks for, prints or stores a secret, API key or token, or a sample that does.
- A code sample that verifies a signature unsafely: parsing the body before verifying, comparing
  signatures in a way that leaks timing, or skipping a timestamp window the provider requires.
- A replay or change instruction that does not ask the person first.
- A provider fact that is wrong in a way that weakens verification.

## How to report

Email support@webhookvault.net with the skill name, the file and line, what an assistant did or
could do, and the client and model if you saw it happen. Please do not open a public issue for a
problem that could be used against someone before it is fixed.

For a problem in the WebhookVault service itself rather than these skills, use the same address.

## What happens next

You get a reply that the report arrived. A confirmed problem is fixed in this repository and the
fix is described in the changelog without details that would help someone use it against an
unpatched copy.
