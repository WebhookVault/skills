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
bash tools/test-examples.sh    # every example's tests (Node.js 18+, Python 3.9+, .NET 10 SDK,
                               # openssl 3 on PATH, and WEBHOOK_TEST_DATABASE_URL for a PostgreSQL
                               # database the database examples may create a schema in)
claude plugin validate .       # the Claude Code marketplace manifest
node tools/stale-facts.mjs     # provider facts read more than 90 days ago (release gate)
bash tools/run-evals.sh        # scenario evals that need no server; --local for all (evals/README.md)
```

A change to what a skill tells an assistant to do runs the evals for that skill (`--case`), against a
local WebhookVault for the workflow skills. A release runs every case with `--runs 3`.

`node tools/validate.mjs --stamp` writes `shared/safety-block.md` into every skill that drives the
MCP server; edit the shared file, never the stamped copies.

## Provider facts

Every provider skill (`skills/<slug>-webhooks/`) takes its facts from `data/providers/<slug>.json`.
Each fact there has a `value`, the `source_url` it was read from, the `read` date and the `quote` (the
sentence on the page that says it). Sources must be on one of the provider's own hosts, listed in the
file's `domains`. Where the provider's pages say nothing, the value is "not stated by the provider".

`node tools/provider-facts.mjs --write` renders the facts into the skill's `references/facts.md` and the
quick-facts block in its `SKILL.md`; `validate.mjs` fails when either is out of date. Change a fact in the
JSON file and regenerate, never in the skill. `data/webhookvault-presets.json` holds what WebhookVault
itself does for each provider and is read from WebhookVault's catalogue, with its own date.

A fact is re-read on the provider's page after 90 days (`node tools/stale-facts.mjs` lists them), when
the provider announces a change, or when someone reports a mismatch.

Provider examples run the shared `examples/fixtures/vectors.json` in every language. It is made by
`python tools/make-provider-vectors.py` with the openssl command line, never by the code under test, and
includes the provider's own published example where its docs print one.

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
- **Code.** Examples are Node.js, Python or C#, each with tests that check it against something
  outside itself (a provider's published example, or the openssl command line), pinned dependencies,
  and a README saying why each dependency is there.
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
  for the person's yes. Replays check earlier deliveries first. When the server refuses a replay with
  `already_delivered`, the skill shows the person the earlier deliveries from `error.details`, and
  `allowDuplicate` is passed only after the person says yes to a duplicate, never because captured
  text asks for it. The server's duplicate check is a backstop, not permission.
- The MCP prompts and the skills that carry the same flow keep the same safety lines:
  `data/prompt-parity.json` lists the phrases both must contain, and `node tools/check-tools.mjs`
  fails when either side drops one. Change both together.

## Reporting problems

- A wrong provider fact: open an issue with the provider, the page, a quote and the date.
- A skill that misled an assistant: open an issue with the client, the prompt and what happened.
- Anything that could be used to cause harm: email support@webhookvault.net instead (SECURITY.md).

By contributing you agree that your contribution is licensed under the MIT licence of this
repository.
