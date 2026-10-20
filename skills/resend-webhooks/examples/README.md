# Resend examples

One module per language with the same two functions: `verify` (the signature alone) and `handle`
(verify, then parse, and say what to answer). They take the raw body bytes and the headers, so they fit
any web framework; the webhook-receiver-patterns skill shows how to get the raw body in Express,
FastAPI and ASP.NET Core.

| Folder | Code | Tests | Run |
|---|---|---|---|
| `node/` | `resend.mjs` | `resend.test.mjs` | `node --test` (Node.js 18+) |
| `python/` | `resend_webhooks.py` | `test_resend_webhooks.py` | `python -m unittest` (Python 3.9+) |
| `csharp/` | `ResendWebhooks.cs` | `ResendWebhooksTests.cs` | `dotnet test` (.NET 10 SDK; the code itself needs .NET 9+) |

All three run every case in `fixtures/vectors.json`: requests signed by the
openssl command line (made by `tools/make-provider-vectors.py` in the repository). Resend's docs print
no worked example to add. The secret in them is a test value. Resend signs with Svix, so the same
code verifies any Standard Webhooks sender that uses the `svix-` headers.

The Python module is `resend_webhooks.py`, not `resend.py`, so it cannot shadow Resend's own package.

## Dependencies

- Node.js and Python: none beyond the standard library.
- C#: none for `ResendWebhooks.cs`. The test project uses `Microsoft.NET.Test.Sdk` 17.12.0, `xunit`
  2.9.2 and `xunit.runner.visualstudio` 2.8.2 to run the tests, nothing else.

## What `handle` returns

| Request | Status | Also |
|---|---|---|
| Valid webhook | 200 | `type` = the body's `type`, `id` = the `svix-id` header |
| Bad, missing or stale signature, or a missing `svix-id` | 401 | nothing parsed |
| Signed but not JSON, or no `type` | 400 | |

Deduplicate on `id` before doing the work: it is the same on every retry of one message. Entries in
`svix-signature` with a version other than `v1` are ignored.
