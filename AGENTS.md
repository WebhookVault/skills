# Notes for agents working in this repository

This repository holds Agent Skills. If you are an AI agent editing it, read CONTRIBUTING.md first;
everything there applies to you. In short:

- Run `node tools/validate.mjs` and `node tools/check-tools.mjs` after every change and fix every
  error before you finish. Do not weaken a check to make it pass.
- Never invent an MCP tool, an argument, an error code, a product behaviour or a provider fact.
  WebhookVault facts come from https://docs.webhookvault.net and the contract snapshot in
  `data/mcp-tools.snapshot.json`; provider facts come from the provider's own pages, with a read
  date.
- Keep each skill installable alone: no links outside its folder except full GitHub URLs.
- The safety block in `shared/safety-block.md` is stamped into skills by
  `node tools/validate.mjs --stamp`. Edit the shared file, never a stamped copy.
- `data/mcp-tools.snapshot.json` is a copy of https://docs.webhookvault.net/mcp-tools.json. Replace it
  only with a fresh copy of that file, and update `data/mcp-tools.snapshot.meta.json` with it.
- When the server's contract changes, re-read every skill that uses a changed tool, update it, and
  set its `metadata.mcp-contract` to the snapshot date.
- No git operations that change history or the remote unless the maintainer asks.
