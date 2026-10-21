# WebhookVault skills

Agent Skills that teach AI assistants to work with webhooks: how to debug a webhook that never
arrived, test a receiver, read failed deliveries, check signatures, triage monitoring, and design
transformations, using WebhookVault's MCP server and API.

Each skill is a folder with a `SKILL.md` in the open [Agent Skills](https://agentskills.io) format,
so the same files work in Claude Code, Cursor, Codex, VS Code with Copilot, Gemini CLI, Devin
Desktop, Zed, Cline and claude.ai.

## Skills

| Skill | What it does |
|---|---|
| [webhookvault-getting-started](skills/webhookvault-getting-started/SKILL.md) | Checks the connection and plan limits, explains what an assistant can and cannot do, picks the workflow |
| [webhookvault-debug-missing-webhook](skills/webhookvault-debug-missing-webhook/SKILL.md) | Finds where an expected webhook stopped: before WebhookVault, at it, on the way to the receiver, or inside the receiver |
| [webhookvault-test-receiver](skills/webhookvault-test-receiver/SKILL.md) | Captures what a sender really sends on a temporary endpoint, then replays it to an existing action with the person's agreement |
| [webhookvault-inspect-deliveries](skills/webhookvault-inspect-deliveries/SKILL.md) | Reads failed and dead-lettered deliveries and says who fixes what |
| [webhookvault-check-verification](skills/webhookvault-check-verification/SKILL.md) | Explains failed, unsigned and unverifiable signature verdicts |
| [webhookvault-watchdog-triage](skills/webhookvault-watchdog-triage/SKILL.md) | Explains watchdog states, checks whether a stream really stopped, resumes a paused watchdog with consent |
| [webhookvault-forwarding-and-transformations](skills/webhookvault-forwarding-and-transformations/SKILL.md) | Designs and previews transformation rules on real captured requests |
| [webhookvault-setup-endpoint](skills/webhookvault-setup-endpoint/SKILL.md) | Walks through creating an endpoint, pointing a provider at it and confirming the first capture |
| [webhookvault-ci-await-testing](skills/webhookvault-ci-await-testing/SKILL.md) | Asserts in CI that a webhook fires, with a self-expiring endpoint and one blocking API call |

General webhook engineering, for any sender and any receiver, no WebhookVault needed:

| Skill | What it does |
|---|---|
| [webhook-signature-verification](skills/webhook-signature-verification/SKILL.md) | Verifies every common signature scheme correctly, with tested Node.js, Python and C# code checked against openssl and the senders' own published examples |
| [webhook-receiver-patterns](skills/webhook-receiver-patterns/SKILL.md) | The handler sequence (size cap, raw body, verify, deduplicate, acknowledge, process later), with tested Express, FastAPI and ASP.NET Core skeletons |
| [webhook-idempotency](skills/webhook-idempotency/SKILL.md) | Processes each event at most once: the dedupe key, an insert-first claim in the same transaction, concurrent duplicates, partial failure, tested on PostgreSQL |
| [webhook-retries-and-responses](skills/webhook-retries-and-responses/SKILL.md) | Status codes and timing for receivers; backoff with full jitter, Retry-After, budgets and dead letters for senders, with tested code |
| [webhook-event-ordering](skills/webhook-event-ordering/SKILL.md) | Out-of-order webhooks: compare versions before writing, tombstones for deletes, fetching current state, reconciliation, tested on PostgreSQL |
| [webhook-hostile-payloads](skills/webhook-hostile-payloads/SKILL.md) | Payload text is written by strangers: escaping for Slack, Discord, Teams, Telegram, HTML, SQL, shells and logs, and keeping injected text from steering an assistant |
| [webhook-testing-strategy](skills/webhook-testing-strategy/SKILL.md) | Testing receivers: real captured samples as scrubbed fixtures, signed test requests, and the duplicate, ordering, failure and hostile-text cases |

Claude Code installs the general skills with `/plugin install webhook-engineering@webhookvault-skills`.

One skill per sender, each with its signature scheme, events, retries and pitfalls. Every fact names the
sender's page it came from, the date it was read and the sentence that says it, and each skill has tested
Node.js, Python and C# handlers:

| Skill | Signature |
|---|---|
| [stripe-webhooks](skills/stripe-webhooks/SKILL.md) | `Stripe-Signature`, HMAC-SHA256 over timestamp and body |
| [github-webhooks](skills/github-webhooks/SKILL.md) | `X-Hub-Signature-256`, HMAC-SHA256 over the body |
| [shopify-webhooks](skills/shopify-webhooks/SKILL.md) | `X-Shopify-Hmac-Sha256`, base64 HMAC-SHA256 over the body |
| [slack-webhooks](skills/slack-webhooks/SKILL.md) | `X-Slack-Signature`, HMAC-SHA256 over version, timestamp and body |
| [twilio-webhooks](skills/twilio-webhooks/SKILL.md) | `X-Twilio-Signature`, HMAC-SHA1 over the URL and parameters |
| [sendgrid-webhooks](skills/sendgrid-webhooks/SKILL.md) | ECDSA over timestamp and body |
| [resend-webhooks](skills/resend-webhooks/SKILL.md) | Standard Webhooks (`svix-*` headers) |
| [paddle-webhooks](skills/paddle-webhooks/SKILL.md) | `Paddle-Signature`, HMAC-SHA256 over timestamp and body |
| [paypal-webhooks](skills/paypal-webhooks/SKILL.md) | RSA certificate signature over ids, time and CRC-32 |
| [discord-webhooks](skills/discord-webhooks/SKILL.md) | Ed25519 over timestamp and body |
| [lemonsqueezy-webhooks](skills/lemonsqueezy-webhooks/SKILL.md) | `X-Signature`, HMAC-SHA256 over the body |
| [woocommerce-webhooks](skills/woocommerce-webhooks/SKILL.md) | `X-WC-Webhook-Signature`, base64 HMAC-SHA256 over the body |

Claude Code installs them with `/plugin install webhook-providers@webhookvault-skills`.

## What the skills need

- **The MCP server** for most of the skills: `https://mcp.webhookvault.net`, connected with an
  **Agent access** key from the API keys page of the app (https://app.webhookvault.net). Agent
  access needs a plan with API access. Setup per client is in
  [the MCP guide](https://docs.webhookvault.net/documentation/mcp).
- **The API** for `webhookvault-ci-await-testing`, with a **Developer access** key.

The assistant only ever reads, creates temporary test endpoints, waits for requests, replays to
actions a person set up, and resumes paused watchdogs. It cannot delete, pause, reconfigure or reach
secrets, keys or billing.

## Install

### Claude Code

As a plugin marketplace:

```
/plugin marketplace add WebhookVault/skills
/plugin install webhookvault@webhookvault-skills
```

The skills then appear as `/webhookvault:<skill>`. Or copy a skill folder to `~/.claude/skills/`
(every project) or `.claude/skills/` (one project).

### Cursor, Codex, VS Code with Copilot, Gemini CLI, Devin Desktop, Zed

Copy a skill folder from `skills/` to `.agents/skills/` in the project, or `~/.agents/skills/` for
every project. Each of these clients documents reading that location.

### Cline

Copy a skill folder to `.cline/skills/` in the project, or `~/.cline/skills/`.

### claude.ai

Zip one skill folder (the zip holds the folder itself, for example `webhookvault-test-receiver/`),
then in claude.ai open Customize, Skills, and upload it. Code execution must be on.

### A third-party installer

`npx skills add WebhookVault/skills` (the `skills` package from vercel-labs) installs into many
clients at once. It is not ours, runs a package from npm, and collects anonymous usage data unless
`DISABLE_TELEMETRY=1` or `DO_NOT_TRACK=1` is set. Copying a folder needs nothing extra.

## Safety

Webhook payloads are written by whoever sends them, so a payload can hold text aimed at an
assistant. Every skill that reads captured data tells the assistant to treat it as data, never as
instructions, never to ask for secrets, and to ask before any change. The WebhookVault MCP server
returns third-party text under a field named `untrusted`, redacts credentials and masks card
numbers. Report a skill that gets this wrong to support@webhookvault.net (see
[SECURITY.md](SECURITY.md)).

This repository contains deliberate attack samples, labelled as such wherever they appear: the
injected text in the examples' fixtures, the payloads `webhook-hostile-payloads` escapes, and the
seed data and failing receiver under `evals/local`. They exist so the examples and the evals can prove an
assistant reports injected text instead of obeying it. None of them is an instruction to an
assistant, and none carries a real secret or real personal data.

## Links

- Documentation: https://docs.webhookvault.net
- The MCP server: https://docs.webhookvault.net/documentation/mcp
- Tool reference: https://docs.webhookvault.net/documentation/mcp-tools
- API reference: https://docs.webhookvault.net/api-reference

## Licence

MIT, for the text and code in this repository.
Provider names are used only to identify the provider.
