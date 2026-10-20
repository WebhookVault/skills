# GitHub examples

One module per language with the same two functions: `verify` (the signature alone) and `handle`
(verify, then parse, and say what to answer). They take the raw body bytes and the headers, so they fit
any web framework; the webhook-receiver-patterns skill shows how to get the raw body in Express,
FastAPI and ASP.NET Core.

| Folder | Code | Tests | Run |
|---|---|---|---|
| `node/` | `github.mjs` | `github.test.mjs` | `node --test` (Node.js 18+) |
| `python/` | `github_webhooks.py` | `test_github_webhooks.py` | `python -m unittest` (Python 3.9+) |
| `csharp/` | `GitHubWebhooks.cs` | `GitHubWebhooksTests.cs` | `dotnet test` (.NET 10 SDK; the code itself needs .NET 9+) |

All three run every case in `fixtures/vectors.json`: requests signed by the
openssl command line (made by `tools/make-provider-vectors.py` in the repository), plus the worked
example from GitHub's "Validating webhook deliveries" page. All secrets in them are test values.

The Python module is `github_webhooks.py` so the name stays clear of any GitHub client package.

## Dependencies

- Node.js and Python: none beyond the standard library.
- C#: none for `GitHubWebhooks.cs`. The test project uses `Microsoft.NET.Test.Sdk` 17.12.0, `xunit`
  2.9.2 and `xunit.runner.visualstudio` 2.8.2 to run the tests, nothing else.

## What `handle` returns

| Request | Status | Also |
|---|---|---|
| Valid delivery | 200 | `type` = `X-GitHub-Event`, `action` = the body's `action` (null when it has none), `id` = `X-GitHub-Delivery` |
| Bad or missing `X-Hub-Signature-256` (the SHA-1 header is never accepted) | 401 | nothing parsed |
| Signed but no `X-GitHub-Event`, or not a JSON object | 400 | |

There is no timestamp, so deduplicate on `id` (a redelivery keeps the same one) and answer within ten
seconds.
