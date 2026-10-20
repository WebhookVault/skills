# Paddle examples

One module per language with the same two functions: `verify` (the signature alone) and `handle`
(verify, then parse, and say what to answer). They take the raw body bytes and the headers, so they fit
any web framework; the webhook-receiver-patterns skill shows how to get the raw body in Express,
FastAPI and ASP.NET Core.

| Folder | Code | Tests | Run |
|---|---|---|---|
| `node/` | `paddle.mjs` | `paddle.test.mjs` | `node --test` (Node.js 18+) |
| `python/` | `paddle_webhooks.py` | `test_paddle_webhooks.py` | `python -m unittest` (Python 3.9+) |
| `csharp/` | `PaddleWebhooks.cs` | `PaddleWebhooksTests.cs` | `dotnet test` (.NET 10 SDK; the code itself needs .NET 9+) |

All three run every case in `fixtures/vectors.json`: requests signed by the
openssl command line (made by `tools/make-provider-vectors.py` in the repository). Paddle's docs print
no worked example to add. The secret in them is a test value. The vectors use Paddle's five second
timestamp window, including a case exactly at the edge and cases just outside it in both directions.

The Python module is `paddle_webhooks.py`, not `paddle.py`, so it cannot shadow Paddle's own package.

## Dependencies

- Node.js and Python: none beyond the standard library.
- C#: none for `PaddleWebhooks.cs`. The test project uses `Microsoft.NET.Test.Sdk` 17.12.0, `xunit`
  2.9.2 and `xunit.runner.visualstudio` 2.8.2 to run the tests, nothing else.

## What `handle` returns

| Request | Status | Also |
|---|---|---|
| Valid notification | 200 | `type` = `event_type`, `id` = `event_id` |
| Bad, missing or stale signature, or no `h1` | 401 | nothing parsed |
| Signed but not JSON, or no `event_type` or `event_id` | 400 | |

Deduplicate on `id` before doing the work. While a secret is being rotated Paddle sends two `h1`
values; any one matching is enough.
