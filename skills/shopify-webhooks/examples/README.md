# Shopify examples

One module per language with the same two functions: `verify` (the signature alone) and `handle`
(verify, then parse, and say what to answer). They take the raw body bytes and the headers, so they fit
any web framework; the webhook-receiver-patterns skill shows how to get the raw body in Express,
FastAPI and ASP.NET Core.

| Folder | Code | Tests | Run |
|---|---|---|---|
| `node/` | `shopify.mjs` | `shopify.test.mjs` | `node --test` (Node.js 18+) |
| `python/` | `shopify_webhooks.py` | `test_shopify_webhooks.py` | `python -m unittest` (Python 3.9+) |
| `csharp/` | `ShopifyWebhooks.cs` | `ShopifyWebhooksTests.cs` | `dotnet test` (.NET 10 SDK; the code itself needs .NET 8+) |

All three run every case in `fixtures/vectors.json`: requests signed by the
openssl command line (made by `tools/make-provider-vectors.py` in the repository). Shopify's docs
print no worked example to add. All secrets in them are test values.

The Python module is `shopify_webhooks.py` so the name stays clear of Shopify's own packages.

## Dependencies

- Node.js and Python: none beyond the standard library.
- C#: none for `ShopifyWebhooks.cs`. The test project uses `Microsoft.NET.Test.Sdk` 17.12.0, `xunit`
  2.9.2 and `xunit.runner.visualstudio` 2.8.2 to run the tests, nothing else.

## What `handle` returns

| Request | Status | Also |
|---|---|---|
| Valid webhook | 200 | `type` = `X-Shopify-Topic`, `id` = `X-Shopify-Webhook-Id`, `eventId` = `X-Shopify-Event-Id`, `shop` = `X-Shopify-Shop-Domain` |
| Bad or missing signature (a hex digest is wrong: the header is base64) | 401 | nothing parsed |
| Signed but no topic or webhook id, or not a JSON object | 400 | |

There is no timestamp. Deduplicate on `id`, answer within five seconds and queue the work.
