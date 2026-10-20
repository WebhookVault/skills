# GitHub webhook facts

Generated from `data/providers/github.json` by `tools/provider-facts.mjs`; change the data and regenerate, never this file.
Every fact was read from GitHub's own pages on the date shown, with the sentence it came from. Quotes are verbatim except that long dashes are written as hyphens. "not stated by the provider" means the pages read did not say; it does not mean there is no rule.

## Contents

- [Signature](#signature)
- [Delivery](#delivery)
- [Responding and retries](#responding-and-retries)
- [Events](#events)
- [Setup and testing](#setup-and-testing)
- [Pitfalls the provider warns about](#pitfalls-the-provider-warns-about)
- [In WebhookVault](#in-webhookvault)

## Signature

- **Signature header:** X-Hub-Signature-256 (the older X-Hub-Signature carries a SHA-1 HMAC for compatibility; GitHub recommends the -256 header). Both are sent only when the webhook has a secret configured.
  Read 2026-10-20 from [docs.github.com/en/webhooks/webhook-events-and-payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads): "X-Hub-Signature is provided for compatibility with existing integrations. We recommend that you use the more secure X-Hub-Signature-256 instead."
- **Scheme:** HMAC-SHA256, hex digest, key is the webhook secret.
  Read 2026-10-20 from [docs.github.com/en/webhooks/webhook-events-and-payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads): "This is the HMAC hex digest of the request body, and is generated using the SHA-256 hash function and the secret as the HMAC key."
- **Signed content:** The request body (payload contents) exactly as received; the docs say to handle it as UTF-8 and note payloads can contain unicode. The docs do not say how the signed bytes relate to the form parameter when content type is x-www-form-urlencoded: not stated by the provider.
  Read 2026-10-20 from [docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries): "The hash signature is generated using your webhook's secret token and the payload contents."
- **Header format:** Single value: the literal prefix sha256= followed by the lowercase-looking hex digest (example in the docs: sha256=757107ea...). One signature only; no timestamp element.
  Read 2026-10-20 from [docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries): "GitHub uses an HMAC hex digest to compute the hash. The hash signature always starts with sha256=."
- **Where the secret comes from:** You choose the secret yourself when creating the webhook (Secret field); docs advise a random high-entropy string, stored securely and never hardcoded or committed.
  Read 2026-10-20 from [docs.github.com/en/webhooks/using-webhooks/creating-webhooks](https://docs.github.com/en/webhooks/using-webhooks/creating-webhooks): "You should choose a random string of text with high entropy."
- **Secret scope:** Set on each webhook's own configuration (repository, organization, or the single webhook of a GitHub App). The docs do not use the phrase 'per webhook' for the secret.
  Read 2026-10-20 from [docs.github.com/en/webhooks/using-webhooks/creating-webhooks](https://docs.github.com/en/webhooks/using-webhooks/creating-webhooks): "Each GitHub App has one webhook."
- **Timestamp tolerance:** not stated by the provider (the signature has no timestamp; replay protection is suggested via X-GitHub-Delivery uniqueness)
  Read 2026-10-20 from [docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks](https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks): "To protect against replay attacks, you can use the X-GitHub-Delivery header to ensure that each delivery is unique per event."
- **Secret rotation:** not stated by the provider (no dual-signature or grace-period description found on the pages read)
  Checked 2026-10-20 at [docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries).
- **Raw body:** Verify against the body as received; treat as UTF-8. The page does not use the words 'raw body' in the summary read, only payload contents and UTF-8 handling.
  Read 2026-10-20 from [docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries): "If your language and server implementation specifies a character encoding, ensure that you handle the payload as UTF-8."
- **Header secret required:** The signature headers are only sent if a secret is configured.
  Read 2026-10-20 from [docs.github.com/en/webhooks/webhook-events-and-payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads): "X-Hub-Signature-256: This header is sent if the webhook is configured with a secret."
- **Secret storage:** Keep it out of code and repositories.
  Read 2026-10-20 from [docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries): "Never hardcode a token into an application or push a token to any repository."
- **Comparison note:** Never compare with a plain ==; use a constant-time comparison.
  Read 2026-10-20 from [docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries): "Never use a plain == operator."
- **Official helper (Node.js):** import { Webhooks } from "@octokit/webhooks"; const webhooks = new Webhooks({ secret }); await webhooks.verify(body, signature) (signature taken from the x-hub-signature-256 header)
  Read 2026-10-20 from [docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries): "if (!(await webhooks.verify(body, signature)))"
- **Official helper (Python):** not stated by the provider as an SDK helper; the docs show a manual example using hmac.new(secret_token.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256) and hmac.compare_digest
  Read 2026-10-20 from [docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries): "if not hmac.compare_digest(expected_signature, signature_header):"
- **Official helper (.NET):** not stated by the provider (the page shows Ruby, Python, JavaScript and TypeScript examples only)
  Checked 2026-10-20 at [docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries).
- **Published example:**

  ```json
  {
    "secret": "It's a Secret to Everybody",
    "payload": "Hello, World!",
    "signature": "sha256=757107ea0eb2509fc211221cce984b8a37570b6d7586c22c46f4379c8b043e17",
    "note": "Payload is the 13 characters Hello, World! with no newline. Recomputed during research: it matches."
  }
  ```

  Read 2026-10-20 from [docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries): "secret: It's a Secret to Everybody payload: Hello, World! If your implementation is correct, the signatures that you generate should match the following signature values: signature: 757107ea0eb2509fc211221cce984b8a37570b6d7586c22c46f4379c8b043e17 X-Hub-Signature-256: sha256=757107ea0eb2509fc211221cce984b8a37570b6d7586c22c46f4379c8b043e17"

## Delivery

- **Method and content type:** HTTP POST. Content type chosen when the webhook is created: application/json (JSON as the raw body) or application/x-www-form-urlencoded (JSON sent as a form parameter called payload).
  Read 2026-10-20 from [docs.github.com/en/webhooks/using-webhooks/creating-webhooks](https://docs.github.com/en/webhooks/using-webhooks/creating-webhooks): "application/json will deliver the JSON payload directly as the body of the POST request."
- **Event name:** X-GitHub-Event request header. Many events also have an 'action' field in the body, so check both.
  Read 2026-10-20 from [docs.github.com/en/webhooks/webhook-events-and-payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads): "X-GitHub-Event: The name of the event that triggered the delivery."
- **Delivery or event id:** X-GitHub-Delivery header (a GUID). A redelivery keeps the same X-GitHub-Delivery as the original.
  Read 2026-10-20 from [docs.github.com/en/webhooks/webhook-events-and-payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads): "X-GitHub-Delivery: A globally unique identifier (GUID) to identify the event."
- **Handshake:** A ping event is sent when a webhook is created (event name ping; body has zen, hook_id and hook). It is a confirmation, not a challenge; no response body is required by the docs. Handle it (or ignore it) and return 2xx.
  Read 2026-10-20 from [docs.github.com/en/webhooks/webhook-events-and-payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads): "The ping event is a confirmation from GitHub that you configured the webhook correctly."
- **Events per request:** not stated by the provider as a batching rule; each delivery carries one event named by X-GitHub-Event
  Read 2026-10-20 from [docs.github.com/en/webhooks/webhook-events-and-payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads): "X-GitHub-Event: The name of the event that triggered the delivery."
- **Content type form:** Form encoding wraps the JSON in a field named payload.
  Read 2026-10-20 from [docs.github.com/en/webhooks/using-webhooks/creating-webhooks](https://docs.github.com/en/webhooks/using-webhooks/creating-webhooks): "application/x-www-form-urlencoded will send the JSON payload as a form parameter called payload."
- **User agent:** User-Agent always starts GitHub-Hookshot/
  Read 2026-10-20 from [docs.github.com/en/webhooks/webhook-events-and-payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads): "This header will always have the prefix GitHub-Hookshot/."
- **Id redelivery:** Same id on redelivery.
  Read 2026-10-20 from [docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks](https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks): "If you request a redelivery, the X-GitHub-Delivery header will be the same as in the original delivery."
- **Other headers:** X-GitHub-Hook-ID (webhook id), X-GitHub-Hook-Installation-Target-Type, X-GitHub-Hook-Installation-Target-ID
  Read 2026-10-20 from [docs.github.com/en/webhooks/webhook-events-and-payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads): "X-GitHub-Hook-ID: The unique identifier of the webhook."
- **Handshake on create:** ping is sent on creation.
  Read 2026-10-20 from [docs.github.com/en/webhooks/using-webhooks/creating-webhooks](https://docs.github.com/en/webhooks/using-webhooks/creating-webhooks): "After you create a new webhook, GitHub will send you a simple ping event to let you know you've set up the webhook correctly."
- **Handshake handler note:** Handlers should account for ping.
  Read 2026-10-20 from [docs.github.com/en/webhooks/using-webhooks/handling-webhook-deliveries](https://docs.github.com/en/webhooks/using-webhooks/handling-webhook-deliveries): "as well as the ping event that GitHub sends when you create a webhook."
- **Payload size cap:** 25 MB; larger events are not delivered at all.
  Read 2026-10-20 from [docs.github.com/en/webhooks/webhook-events-and-payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads): "Payloads are capped at 25 MB. If an event generates a larger payload, GitHub will not deliver a payload for that webhook event."

## Responding and retries

- **Expected response:** 2XX (the docs example answers 202).
  Read 2026-10-20 from [docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks](https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks): "Your server should respond with a 2XX response within 10 seconds of receiving a webhook delivery."
- **Response deadline:** 10 seconds; after that GitHub terminates the connection and counts the delivery as failed.
  Read 2026-10-20 from [docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks](https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks): "If your server takes longer than that to respond, then GitHub terminates the connection and considers the delivery a failure."
- **Retries:** No automatic retries: GitHub does not automatically redeliver failed deliveries. You redeliver manually (UI or REST API) for deliveries from the past 3 days.
  Read 2026-10-20 from [docs.github.com/en/webhooks/testing-and-troubleshooting-webhooks/redelivering-webhooks](https://docs.github.com/en/webhooks/testing-and-troubleshooting-webhooks/redelivering-webhooks): "GitHub does not automatically redeliver failed deliveries."
- **Disabling after failures:** not stated by the provider (no page read says GitHub disables a webhook after failures)
  Checked 2026-10-20 at [docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks](https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks).
- **Ordering:** not stated by the provider
  Checked 2026-10-20 at [docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks](https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks).
- **Duplicates:** not stated by the provider as a duplicate-delivery warning. The docs suggest X-GitHub-Delivery to make sure each delivery is unique per event (framed as replay protection), and redeliveries reuse the id.
  Read 2026-10-20 from [docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks](https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks): "you can use the X-GitHub-Delivery header to ensure that each delivery is unique per event."
- **Redelivery window:** 3 days.
  Read 2026-10-20 from [docs.github.com/en/webhooks/testing-and-troubleshooting-webhooks/redelivering-webhooks](https://docs.github.com/en/webhooks/testing-and-troubleshooting-webhooks/redelivering-webhooks): "You can redeliver webhook deliveries that occurred in the past 3 days."
- **Async processing:** Docs recommend queueing so you can answer quickly.
  Read 2026-10-20 from [docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks](https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks): "you may want to set up a queue to process webhook payloads asynchronously."

## Events

Full list: https://docs.github.com/en/webhooks/webhook-events-and-payloads

- **`push`:** A commit or tag was pushed, or a branch or tag deleted, or a repo created from a template.
  Read 2026-10-20 from [docs.github.com/en/webhooks/webhook-events-and-payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads): "This event occurs when there is a push to a repository branch."
- **`pull_request`:** Any activity on a pull request (opened, closed, synchronize, and so on, via the action field).
  Read 2026-10-20 from [docs.github.com/en/webhooks/webhook-events-and-payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads): "This event occurs when there is activity on a pull request."
- **`issues`:** Activity on an issue (opened, closed, labeled and so on).
  Read 2026-10-20 from [docs.github.com/en/webhooks/webhook-events-and-payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads): "This event occurs when there is activity relating to an issue."
- **`issue_comment`:** A comment on an issue or pull request was created, edited or deleted.
  Read 2026-10-20 from [docs.github.com/en/webhooks/webhook-events-and-payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads): "This event occurs when there is activity relating to a comment on an issue or pull request."
- **`release`:** Release activity (published, created, edited, and so on).
  Read 2026-10-20 from [docs.github.com/en/webhooks/webhook-events-and-payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads): "This event occurs when there is activity relating to releases."
- **`workflow_run`:** A GitHub Actions workflow run changed state (requested, in progress, completed).
  Read 2026-10-20 from [docs.github.com/en/webhooks/webhook-events-and-payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads): "This event occurs when there is activity relating to a run of a GitHub Actions workflow."
- **`check_run`:** Activity on a check run.
  Read 2026-10-20 from [docs.github.com/en/webhooks/webhook-events-and-payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads): "This event occurs when there is activity relating to a check run."
- **`installation`:** A GitHub App installation was created, deleted, suspended and so on.
  Read 2026-10-20 from [docs.github.com/en/webhooks/webhook-events-and-payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads): "This event occurs when there is activity relating to a GitHub App installation."
- **`create`:** A branch or tag was created.
  Read 2026-10-20 from [docs.github.com/en/webhooks/webhook-events-and-payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads): "This event occurs when a Git branch or tag is created."
- **`ping`:** Sent once when a webhook is created, to confirm setup.
  Read 2026-10-20 from [docs.github.com/en/webhooks/webhook-events-and-payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads): "This event occurs when you create a new webhook."

## Setup and testing

- **Where the URL goes:** Repository webhook: Settings, Webhooks, Add webhook; set Payload URL, Content type, optional Secret and the events. Organization webhooks need an organization owner. A GitHub App has exactly one webhook, set in its registration.
  Read 2026-10-20 from [docs.github.com/en/webhooks/using-webhooks/creating-webhooks](https://docs.github.com/en/webhooks/using-webhooks/creating-webhooks): "You must be an organization owner to create webhooks in that organization."
- **Test tools:** ping on creation; Recent deliveries list with a Redeliver button (repository admins for repo webhooks, owners for org webhooks); REST API endpoints to redeliver; deliveries from the last 3 days can be redelivered.
  Read 2026-10-20 from [docs.github.com/en/webhooks/testing-and-troubleshooting-webhooks/redelivering-webhooks](https://docs.github.com/en/webhooks/testing-and-troubleshooting-webhooks/redelivering-webhooks): "Only people with admin access to a repository can redeliver webhooks in that repository."
- **Source IP addresses:** Published via the GET /meta REST endpoint; changes occasionally, so refresh the allow list periodically.
  Read 2026-10-20 from [docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks](https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks): "You can use the GET /meta endpoint to find the current list of GitHub's IP addresses."
- **Recent deliveries:** A recent deliveries log exists for troubleshooting; retention not stated on the pages read.
  Read 2026-10-20 from [docs.github.com/en/webhooks/testing-and-troubleshooting-webhooks/troubleshooting-webhooks](https://docs.github.com/en/webhooks/testing-and-troubleshooting-webhooks/troubleshooting-webhooks): "Look at the recent deliveries log for your webhook."

## Pitfalls the provider warns about

- **1:** 10 second budget; GitHub kills the connection and marks the delivery failed. Queue the work.
  Read 2026-10-20 from [docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks](https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks): "If your server takes longer than that to respond, then GitHub terminates the connection and considers the delivery a failure."
- **2:** Failed deliveries are never retried automatically; if your server is down you must redeliver within 3 days.
  Read 2026-10-20 from [docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks](https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks): "If your server goes down, you should redeliver missed webhooks once your server is back up."
- **3:** Use the SHA-256 header, not the SHA-1 one.
  Read 2026-10-20 from [docs.github.com/en/webhooks/webhook-events-and-payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads): "We recommend that you use the more secure X-Hub-Signature-256 instead."
- **4:** Payloads can contain unicode; handle as UTF-8 when verifying.
  Read 2026-10-20 from [docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries): "Webhook payloads can contain unicode characters."
- **5:** Oversized events (over 25 MB) are silently not delivered; docs give create with many branches or tags as an example.
  Read 2026-10-20 from [docs.github.com/en/webhooks/webhook-events-and-payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads): "This may happen, for example, on a create event if many branches or tags are pushed at once."
- **6:** Leave SSL verification enabled; docs say use HTTPS.
  Read 2026-10-20 from [docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks](https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks): "GitHub recommends that you leave SSL verification enabled."
- **7:** Check both the event header and the action field before processing.
  Read 2026-10-20 from [docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks](https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks): "Check the event type and action before processing the event"

## In WebhookVault

What WebhookVault does with GitHub requests, read from its provider catalogue on 2026-10-20. These are facts about WebhookVault, not about GitHub.

- **Signature header it reads:** `X-Hub-Signature-256`
- **Checks the signature:** yes (HMAC-SHA256 hex of the raw body, prefixed sha256=)
- **Secret field label:** Signing secret
- **Where it finds the event name:** header `X-GitHub-Event`
- **Where the capture URL goes in GitHub:** Repository or organisation Settings > Webhooks > Add webhook (content type application/json)
