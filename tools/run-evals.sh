#!/usr/bin/env bash
# Runs the skill evals with `claude plugin eval` (Claude Code 2.1.300 or later).
#
#   bash tools/run-evals.sh [options...]           the cases that need no server (provider, general, api)
#   bash tools/run-evals.sh --local [options...]   every case, against a running WebhookVault MCP server
#
# --local needs EVAL_WEBHOOKVAULT_MCP_URL (for example http://localhost:5060/) and
# EVAL_WEBHOOKVAULT_AGENT_KEY (an Agent access key for a workspace seeded as evals/README.md says).
# Never point it at a production workspace: the consent cases create a temporary endpoint and resume
# a watchdog. Further options go to `claude plugin eval` (for example --case 'inspect-*', --runs 3,
# --concurrency 2, --model sonnet). Every case run is a Claude session billed to your account;
# EVAL_MAX_COST_USD (default 10) stops a run that costs more than it should.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

local_mode=false
if [ "${1:-}" = "--local" ]; then local_mode=true; shift; fi

node tools/eval-harness.mjs

args=(--no-publish --trust-plugin --ablation none --max-cost-usd "${EVAL_MAX_COST_USD:-10}")
if $local_mode; then
  : "${EVAL_WEBHOOKVAULT_MCP_URL:?set EVAL_WEBHOOKVAULT_MCP_URL to the MCP server, for example http://localhost:5060/}"
  : "${EVAL_WEBHOOKVAULT_AGENT_KEY:?set EVAL_WEBHOOKVAULT_AGENT_KEY to an Agent access key}"
  args+=(--mocks off --allow-tools "mcp__plugin_wv_webhookvault__*")
else
  # The workflow cases read a seeded workspace through the MCP server; without one, only the cases
  # that need no server run.
  args+=(--mocks off --tag provider --tag general --tag api)
fi

# --trust-plugin: the harness was built from this repository's own files a moment ago.
exec claude plugin eval evals/.harness "${args[@]}" "$@"
