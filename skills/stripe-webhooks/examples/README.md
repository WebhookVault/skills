# Stripe examples

One module per language with the same two functions: `verify` (the signature alone) and `handle`
(verify, then parse, and say what to answer). They take the raw body bytes and the headers, so they fit
any web framework; the webhook-receiver-patterns skill shows how to get the raw body in Express,
FastAPI and ASP.NET Core.

| Folder | Code | Tests | Run |
|---|---|---|---|
| `node/` | `stripe.mjs` | `stripe.test.mjs` | `node --test` (Node.js 18+) |
| `python/` | `stripe_webhooks.py` | `test_stripe_webhooks.py` | `python -m unittest` (Python 3.9+) |
| `csharp/` | `StripeWebhooks.cs` | `StripeWebhooksTests.cs` | `dotnet test` (.NET 10 SDK; the code itself needs .NET 9+) |

All three run every case in `fixtures/vectors.json`: requests signed by the
openssl command line (made by `tools/make-provider-vectors.py` in the repository). Stripe's docs
print no worked example to add. All secrets in them are test values.

The Python module is `stripe_webhooks.py`, not `stripe.py`, so it cannot shadow Stripe's own package.

## Dependencies

- Node.js and Python: none beyond the standard library.
- C#: none for `StripeWebhooks.cs`. The test project uses `Microsoft.NET.Test.Sdk` 17.12.0, `xunit`
  2.9.2 and `xunit.runner.visualstudio` 2.8.2 to run the tests, nothing else.

## What `handle` returns

| Request | Status | Also |
|---|---|---|
| Valid event | 200 | `type` = the event's `type`, `id` = the event's `id` |
| Two `v1` signatures (a secret is being rolled) | 200 | accepted when either matches |
| Bad, missing or `v0`-only signature, no or repeated `t`, or a timestamp more than 300 seconds away | 401 | nothing parsed |
| Signed but not a JSON object with a string `id` and `type` | 400 | |

Deduplicate on `id` before doing the work, and answer with a 2xx quickly.
