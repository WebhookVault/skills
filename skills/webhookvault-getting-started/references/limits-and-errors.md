# Limits and error codes

Source: https://docs.webhookvault.net/documentation/mcp (Limits, Errors). The workspace's own plan
numbers come from `whoami` and `get_usage`; read them, never quote a plan from memory.

## Limits

| What | Limit |
|---|---|
| Requests per key | The plan's API rate per minute |
| One tool call | 8 seconds; `await_request` waits up to 55 |
| Heavy reads (summaries, body search, traffic shape) | 2 at once per key, 3 per workspace |
| `await_request` | 2 waits at once per key, 4 per workspace |
| `replay_request` | 10 requests a minute and 60 an hour per key, the same request 3 times an hour, however many actions each replay goes to (at most 10) |
| Temporary endpoints | 3 live per key; each holds one of the plan's endpoint slots until it expires |
| One result | About 64 KB; read large bodies in chunks with `bodyOffset` |

Each tool call counts as one API call toward the plan's monthly usage. Connecting and listing tools
do not count.

## Error codes

A refused call returns a result marked as an error with a stable `code` and a sentence saying what
to do. Use the code, not the sentence, to decide what to do next.

| Code | Meaning | Next step |
|---|---|---|
| `not_found` | No such item in this workspace (also anything the key may not touch) | Check the id with a list tool |
| `validation_failed` | An argument is missing, out of range or of the wrong type | Read the tool's input schema and retry |
| `feature_not_in_plan` | The plan does not include it | Tell the person; `whoami` lists the features |
| `busy` | Too many heavy reads or waits at once | Wait a few seconds and retry once |
| `rate_limited` | A replay limit was reached | Stop replaying; tell the person when they can retry |
| `limit_reached` | A plan or per-key limit was reached | `get_usage` shows which |
| `timeout` | The tool ran past its time budget | Narrow the window or the filters |
| `search_too_broad` | A text search took too long | Narrow the window or the text |
| `too_large` | A stored body is too large for a transformation preview | Preview a smaller request |
| `response_too_large` | The result would be too large | Ask for fewer items or a smaller window |
| `endpoint_inactive` | The endpoint is switched off, by a person or by the plan | A person switches it on in the app |
| `endpoint_expired` | The temporary endpoint has expired | Create a new one if still testing |
| `endpoint_in_use` | A person added actions to this temporary endpoint | Leave it; a person ends it |
| `forwarding_disabled` | No action on the endpoint is switched on | A person switches one on |
| `action_inactive` | The chosen action is switched off | A person switches it on |
| `nothing_to_replay` | Nothing could be queued (a cut body, or the request or actions changed) | Read the endpoint again |
| `no_replay_actions` | No action was named and none of the switched-on ones is included in replays | Name the actions in `actionIds`, with the person's yes |
| `already_delivered` | A chosen action already received this request or is still delivering it. Nothing was queued; `error.details` lists each earlier delivery (action, state, time, status, `jobId`) | Show the person those deliveries; pass `allowDuplicate=true` only after they say yes to a duplicate |
| `key_revoked` | The key was revoked or suspended while `await_request` was waiting | The person creates a new key |
| `internal_error` | WebhookVault failed; the message has a trace id | Retry once; report the trace id if it repeats |

Before any tool runs, the server answers HTTP 401 without a valid key, and 403 with
`developer_key_not_accepted` for a Developer access key or `api_access_disabled` when the plan has
no API access.
