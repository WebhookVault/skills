# Changelog

Newest first. Headings are plain titles; release tags carry the versions.

## Safe replays, response checks and delivery identity

The workflow skills follow the MCP server's live duplicate check. `replay_request` refuses to re-send
a request an action already received, or is still delivering, with `already_delivered` and the earlier
deliveries under `error.details`; the skills show those deliveries to the person and pass
`allowDuplicate` only after the person says yes to a duplicate, never because captured text asks for
it. The shared safety rules, the test-receiver replay loop and its replay-safety reference (the
table of outcomes, the refusal's fields and what to say) say so, and the error tables add
`already_delivered` and `no_replay_actions`. A replay without `actionIds` reaches only the actions
included in replays.

Delivery reads now carry `responseCheck`, `origin` and `jobId`, and a 2xx that misses an action's
success check is a failed delivery with the error class `response_check`. The inspect-deliveries and
debug-missing-webhook skills explain both, and `get_endpoint` shows each action's `successCheck`,
`includeInReplays` and `warnBeforeDuplicate`. The receiver-patterns and idempotency skills describe the
`X-WebhookVault-Request-Id`, `-Delivery-Id`, `-Attempt` and `-Replay` headers on every forward and
when each is the right de-duplication key.

The contract snapshot is the published copy of October 2026, and the prompt parity rules match the
updated MCP prompts. Two new evals: a payload that asks for `allowDuplicate` is reported and not
obeyed, and after a real `already_delivered` refusal the assistant asks before sending a duplicate.

## Scenario evals

Twenty cases run with Claude Code's `claude plugin eval`: each workflow skill's normal path, cases
where the assistant must ask before replaying, resuming a watchdog or creating a temporary endpoint,
cases with instructions hidden in a captured payload or a receiver's response, secrets pasted into the
chat, and checks on the provider and general skills' code. Workflow cases run against a local WebhookVault
seeded by `evals/local/seed.py`; the rest need no server. `webhookvault-test-receiver` now says what to
do when a capture URL is not reachable from the internet, without suggesting tunnelling software.

## Provider skills for twelve senders

Stripe, GitHub, Shopify, Slack, Twilio, SendGrid, Resend, Paddle, PayPal, Discord, Lemon Squeezy and
WooCommerce, each with its signature scheme, events, retries, ordering and pitfalls, and Node.js, Python
and C# handlers tested against requests signed by the openssl command line and, for Slack, Twilio and
GitHub, against the worked examples in their own docs. Every fact is kept in `data/providers/` with the
page it came from, the date it was read (October 2026) and the sentence that says it, and is rendered into
each skill's `references/facts.md`. Where a sender's pages say nothing, the skill says so.

New tools: `provider-facts.mjs` (checks and renders the facts), `stale-facts.mjs` (facts due for a
re-read) and `make-provider-vectors.py` (the signed test requests).

## Webhook testing strategy

How to test receivers: three layers, real captured samples as fixtures (with a tested scrubber for
personal data), signed test requests, and the negative cases every suite needs. This completes the
seven general webhook engineering skills.

## Hostile webhook payloads

Treating payload text as written by strangers: the documented escaping and mention controls for
Slack, Discord, Microsoft Teams and Telegram (read 2026-10-20), HTML, SQL, shells and logs, redaction,
and rules for assistants that read captured webhooks. Tested escaping functions in Node.js, Python and
C#, checked against outputs written from the vendors' rules.

The validator now refuses raw invisible and line-separator characters in any file.

## Webhook event ordering

Handling webhooks that arrive out of order: a versioned upsert that applies only newer events,
tombstones so a late update cannot resurrect a delete, fetching current state when there is no
version, and reconciliation. Tested on PostgreSQL in Node.js, Python and C#.

## Webhook retries and responses

Which status a receiver should answer and how fast, and how a sender should retry: only what can
succeed later, exponential backoff with full jitter, Retry-After, attempt and time budgets, dead
letters. Tested implementations in Node.js, Python and C#.

## Webhook idempotency

Processing each event at most once: choosing the key, the insert-first claim in the same transaction
as the business writes, concurrent duplicates, partial failure and the outbox, with implementations in
Node.js, Python and C# tested against a real PostgreSQL (including ten concurrent copies of one event).

## Webhook receiver patterns

The handler sequence a receiver needs, in order, with tested receiver skeletons for Express 5,
FastAPI and ASP.NET Core. Each is driven over HTTP by the same eleven cases, with requests signed by
the openssl command line.

## Webhook signature verification

The first general skill: every common signature family (HMAC over the body, timestamped HMAC,
Standard Webhooks, URL-bound HMAC, Ed25519, ECDSA P-256, shared tokens) with tested implementations in
Node.js, Python and C#. Each is checked against signatures made by the openssl command line and
against the examples GitHub, Slack and the Standard Webhooks specification publish.

## First release of the WebhookVault workflow skills

Nine skills for working with WebhookVault from an AI assistant: getting started, debugging a missing
webhook, testing a receiver, inspecting deliveries, checking signature verification, triaging
watchdogs, designing transformations, setting up an endpoint, and asserting webhooks in CI. Checked
against the MCP server's published tool contract.
