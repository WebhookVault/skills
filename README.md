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
numbers. Report a skill that gets this wrong to security@webhookvault.net (see
[SECURITY.md](SECURITY.md)).

## Links

- Documentation: https://docs.webhookvault.net
- The MCP server: https://docs.webhookvault.net/documentation/mcp
- Tool reference: https://docs.webhookvault.net/documentation/mcp-tools
- API reference: https://docs.webhookvault.net/api-reference

## Licence

MIT, for the text and code in this repository. The WebhookVault name and logo are not licensed.
Provider names are used only to identify the provider.
