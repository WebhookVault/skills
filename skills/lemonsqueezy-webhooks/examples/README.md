# Lemon Squeezy examples

One module per language with the same two functions: `verify` (the signature alone) and `handle`
(verify, then parse, and say what to answer). They take the raw body bytes and the headers, so they fit
any web framework; the webhook-receiver-patterns skill shows how to get the raw body in Express,
FastAPI and ASP.NET Core.

| Folder | Code | Tests | Run |
|---|---|---|---|
| `node/` | `lemonsqueezy.mjs` | `lemonsqueezy.test.mjs` | `node --test` (Node.js 18+) |
| `python/` | `lemonsqueezy_webhooks.py` | `test_lemonsqueezy_webhooks.py` | `python -m unittest` (Python 3.9+) |
| `csharp/` | `LemonSqueezyWebhooks.cs` | `LemonSqueezyWebhooksTests.cs` | `dotnet test` (.NET 10 SDK; the code itself needs .NET 9+) |

All three run every case in `fixtures/vectors.json`: requests signed by the
openssl command line (made by `tools/make-provider-vectors.py` in the repository). Lemon Squeezy's docs
print no worked example to add. All secrets in them are test values.

The Python module is `lemonsqueezy_webhooks.py` so the name stays clear of any Lemon Squeezy client package.

## Dependencies

- Node.js and Python: none beyond the standard library.
- C#: none for `LemonSqueezyWebhooks.cs`. The test project uses `Microsoft.NET.Test.Sdk` 17.12.0, `xunit`
  2.9.2 and `xunit.runner.visualstudio` 2.8.2 to run the tests, nothing else.

## What `handle` returns

| Request | Status | Also |
|---|---|---|
| Valid webhook | 200 | `type` = the signed body's `meta.event_name`, `id` = null (Lemon Squeezy sends none), `resource` = `<data.type>/<data.id>` (null when either is missing) |
| Bad or missing `X-Signature` | 401 | nothing parsed |
| Signed but no `meta.event_name`, an `X-Event-Name` header that disagrees with it, or not a JSON object | 400 | |

The event name comes from the signed body, never from the unsigned `X-Event-Name` header. With no
event id, skip a body you have already processed (a hash of it catches resent requests), apply only
state newer than what you hold for `resource`, and answer quickly.
