# SendGrid examples

One module per language with the same functions: load the public key once, `verify` (the signature
alone) and `handle` (verify, then parse the batch, and say what to answer). They take the raw body
bytes and the headers, so they fit any web framework; the webhook-receiver-patterns skill shows how to
get the raw body in Express, FastAPI and ASP.NET Core.

| Folder | Code | Tests | Run |
|---|---|---|---|
| `node/` | `sendgrid.mjs` | `sendgrid.test.mjs` | `node --test` (Node.js 18+) |
| `python/` | `sendgrid_webhooks.py` | `test_sendgrid_webhooks.py` | `pip install -r requirements.txt`, then `python -m unittest` (Python 3.9+) |
| `csharp/` | `SendGridWebhooks.cs` | `SendGridWebhooksTests.cs` | `dotnet test` (.NET 10 SDK; the code itself needs .NET 8+) |

All three run every case in `fixtures/vectors.json`: batches signed by the
openssl command line with a P-256 key made for that run (by `tools/make-provider-vectors.py` in the
repository). Only the public half of the key is kept. SendGrid's docs print no worked example to add.

The Python module is `sendgrid_webhooks.py`, not `sendgrid.py`, so it cannot shadow SendGrid's own
package.

## Dependencies

- Node.js: none beyond the standard library (`crypto.verify` checks ECDSA).
- Python: `cryptography` 50.0.2, because the standard library has no elliptic curve signatures.
- C#: none for `SendGridWebhooks.cs` (`System.Security.Cryptography.ECDsa`). The test project uses
  `Microsoft.NET.Test.Sdk` 17.12.0, `xunit` 2.9.2 and `xunit.runner.visualstudio` 2.8.2.

## What `handle` returns

| Request | Status | Also |
|---|---|---|
| Valid batch | 200 | `events`: each event's `type` (`event`) and `id` (`sg_event_id`) |
| Bad or missing signature, or a body changed after signing | 401 | nothing parsed |
| Signed, but not a JSON array of objects | 400 | |
