# Slack examples

One module per language with the same two functions: `verify` (the signature alone) and `handle`
(verify, then parse, and say what to answer). They take the raw body bytes and the headers, so they fit
any web framework; the webhook-receiver-patterns skill shows how to get the raw body in Express,
FastAPI and ASP.NET Core.

| Folder | Code | Tests | Run |
|---|---|---|---|
| `node/` | `slack.mjs` | `slack.test.mjs` | `node --test` (Node.js 18+) |
| `python/` | `slack.py` | `test_slack.py` | `python -m unittest` (Python 3.9+) |
| `csharp/` | `SlackWebhooks.cs` | `SlackWebhooksTests.cs` | `dotnet test` (.NET 10 SDK; the code itself needs .NET 9+) |

All three run every case in `fixtures/vectors.json`: requests signed by the
openssl command line (made by `tools/make-provider-vectors.py` in the repository), plus the worked
example from Slack's "Verifying requests from Slack" page. All secrets in them are test values.

## Dependencies

- Node.js and Python: none beyond the standard library.
- C#: none for `SlackWebhooks.cs`. The test project uses `Microsoft.NET.Test.Sdk` 17.12.0, `xunit`
  2.9.2 and `xunit.runner.visualstudio` 2.8.2 to run the tests, nothing else.

## What `handle` returns

| Request | Status | Also |
|---|---|---|
| Valid `event_callback` | 200 | `type` = `event.type`, `id` = `event_id` |
| Valid `url_verification` | 200 | `reply` = the challenge, to send back as the body |
| Valid interactivity form | 200 | `type` = the payload's `type`, `id` = null (no event id) |
| Bad, missing or stale signature | 401 | nothing parsed |
| Signed but not JSON, or no event | 400 | |

Deduplicate on `id` before doing the work, and answer within three seconds.
