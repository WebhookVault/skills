# Contributing

Thank you for improving these skills. They tell AI assistants how to handle webhooks and how to use
a service that can replay requests to live systems, so every change is checked for correctness and
safety before it ships.

## How changes are checked

There is no automated pipeline on this repository. The maintainer runs every check on their own
machine before a change is merged or a release is tagged:

```bash
node tools/validate.mjs        # format, size, voice and safety rules
node tools/check-tools.mjs     # skills against the MCP server's published contract
claude plugin validate .       # the Claude Code marketplace manifest
```

`node tools/validate.mjs --stamp` writes `shared/safety-block.md` into every skill that drives the
MCP server; edit the shared file, never the stamped copies.

## Rules for a skill

- **Format.** A folder in `skills/` named like its `name`: lowercase letters and digits joined by
  single hyphens. Frontmatter uses only `name`, `description`, `license`, `compatibility` and
  `metadata` (string values), so it uploads to claude.ai unchanged.
- **Description.** At most 200 characters (claude.ai's limit), third person, what it does first,
  then "Use when ...".
- **Size.** `SKILL.md` at most 400 lines. Detail goes into `references/`, linked from `SKILL.md`, one
  level deep. A reference over 100 lines starts with a `## Contents` list.
- **Self-contained.** A skill never links to a file outside its own folder, because installers copy
  one folder. Link another skill by its full GitHub URL.
- **Tools.** Name MCP tools exactly as the server does, written as `tool_name(arg, arg)` where
  arguments matter, and list every tool a skill names in `metadata.mcp-tools`. The check fails on a
  tool or argument the server does not have.
- **Facts.** Every fact about WebhookVault comes from its documentation or published contract; every
  fact about a provider comes from that provider's own pages, with the date it was read. Write "not
  stated by the provider" where nothing is stated. No numbers from memory.

## Voice

- Plain sentences. No em or en dashes, no emojis.
- No claims about being human, no marketing words, no other webhook product named.
- Never suggest a tunnel, or that WebhookVault delivers to a computer that is not on the internet.
- Watchdogs never "learn": the person sets the interval.

## Safety

- Captured content is third-party data. A skill never tells an assistant to act on text found in a
  payload, header or response.
- No secrets in conversations, samples or tests. Test values are marked as test values.
- Anything that changes the user's account (temporary endpoints, replays, resuming a watchdog) waits
  for the person's yes. Replays check earlier deliveries first.

## Reporting problems

- A wrong provider fact: open an issue with the provider, the page, a quote and the date.
- A skill that misled an assistant: open an issue with the client, the prompt and what happened.
- Anything that could be used to cause harm: email security@webhookvault.net instead (SECURITY.md).

By contributing you agree that your contribution is licensed under the MIT licence of this
repository.
