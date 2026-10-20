# WooCommerce examples

One module per language with the same two functions: `verify` (the signature alone) and `handle`
(verify, then parse, and say what to answer). They take the raw body bytes and the headers, so they fit
any web framework; the webhook-receiver-patterns skill shows how to get the raw body in Express,
FastAPI and ASP.NET Core.

| Folder | Code | Tests | Run |
|---|---|---|---|
| `node/` | `woocommerce.mjs` | `woocommerce.test.mjs` | `node --test` (Node.js 18+) |
| `python/` | `woocommerce_webhooks.py` | `test_woocommerce_webhooks.py` | `python -m unittest` (Python 3.9+) |
| `csharp/` | `WooCommerceWebhooks.cs` | `WooCommerceWebhooksTests.cs` | `dotnet test` (.NET 10 SDK; the code itself needs .NET 8+) |

All three run every case in `fixtures/vectors.json`: requests signed by the
openssl command line (made by `tools/make-provider-vectors.py` in the repository). WooCommerce's docs
print no worked example to add. All secrets in them are test values.

The Python module is `woocommerce_webhooks.py` so the name stays clear of any WooCommerce client package.

## Dependencies

- Node.js and Python: none beyond the standard library.
- C#: none for `WooCommerceWebhooks.cs`. The test project uses `Microsoft.NET.Test.Sdk` 17.12.0, `xunit`
  2.9.2 and `xunit.runner.visualstudio` 2.8.2 to run the tests, nothing else.

## What `handle` returns

| Request | Status | Also |
|---|---|---|
| Valid webhook | 200 | `type` = `X-WC-Webhook-Topic`, `id` = `X-WC-Webhook-Delivery-ID` (null when absent) |
| Activation ping: no signature header and a body that is exactly `webhook_id=<digits>` | 200 | `type` = `ping`, `id` = null, nothing processed |
| Bad or missing signature (any other unsigned request, including a longer `webhook_id=` body) | 401 | nothing parsed |
| Signed but no topic, or not a JSON object | 400 | |

There is no timestamp. Deduplicate on `id` when it is present and answer quickly.
