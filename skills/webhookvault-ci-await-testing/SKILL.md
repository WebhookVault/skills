---
name: webhookvault-ci-await-testing
description: Adds a webhook assertion to a CI job with the WebhookVault API: a self-expiring endpoint, trigger, block until it arrives, check the payload. Use when testing in CI that a webhook fires.
license: MIT
compatibility: Uses the WebhookVault API (https://app.webhookvault.net/api/v1) with a Developer access key; plans with API access (Solo and up).
metadata:
  author: "webhookvault"
  version: "0.1.0"
  repository: "https://github.com/WebhookVault/skills"
---

# Assert a webhook in CI

The hard part of testing webhooks is not sending them; it is asserting they arrived. With the
WebhookVault API a CI job creates an endpoint that deletes itself, points the system under test at
it, triggers the action, and makes one blocking call that returns the webhook the moment it lands,
or `204` when it does not.

This uses the API with a **Developer access** key, not the MCP server. An Agent access key is
refused by the API (`agent_key_not_accepted`).

## Prerequisites

- A plan with API access (Solo and up).
- A Developer access key, created on the API keys page of the app, stored in the CI system's secret
  store (for example a repository secret named `WV_KEY`). Never commit it, print it or paste it into
  a chat. Give the CI job its own key so it can be revoked alone.

## The pattern

1. **Create a self-expiring endpoint.** `POST /api/v1/endpoints` with `{"name": "...",
   "ttlSeconds": 900}`. `ttlSeconds` is 60 to 86,400; the endpoint is deleted when it expires, so a
   cancelled job leaves nothing behind. The response carries `id` and the capture `url`.
2. **Point the system under test at the `url` and trigger it.** Whatever makes the webhook fire.
3. **Block until it arrives.** `GET /api/v1/endpoints/{id}/requests/await?timeoutSeconds=60` with
   filters such as `q` (text) and `method`. `200` returns the request; `204` means nothing matching
   arrived in time: fail the job with a clear message.
4. **Assert on the payload.** The request's `body` is the raw body as text; parse it in the test.

Await details, including the race when the webhook can fire before the call starts:
[await-reference.md](references/await-reference.md). Complete scripts in bash, Node.js and Python,
and a job definition: [recipes.md](references/recipes.md).

## Assertions worth making

- It arrived at all, within the time the product promises.
- The event type and the identifiers the test created (an order id, a customer id).
- The signature header is present when the sender signs. Verifying it in the test needs the
  signing secret, which belongs in the CI secret store, never in the repository.
- Exactly one arrived, when duplicates matter: after the first match, await again with `afterId`
  set to its id and a short timeout, and expect `204`.

## Failure output

Print what the job knows without printing secrets: the endpoint id, the filter used, how long it
waited, and on a mismatch the event type and a short excerpt of the body. Do not print headers
wholesale; they may carry the sender's tokens.

## Cost and limits

An await call counts as one API call however long it waits (up to 80 seconds). Creating an
endpoint uses one of the plan's endpoint slots until it expires, so keep `ttlSeconds` short and run
jobs that create endpoints in parallel only within the plan's endpoint limit.

## After the run

A failing job can be investigated from an editor with the WebhookVault MCP server (the
`webhookvault-debug-missing-webhook` skill) while the endpoint has not yet expired.
