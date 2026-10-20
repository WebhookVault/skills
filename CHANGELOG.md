# Changelog

Newest first. Headings are plain titles; release tags carry the versions.

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
