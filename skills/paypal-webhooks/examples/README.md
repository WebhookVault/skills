# PayPal examples

One module per language with the same two functions: `verify` (the signature alone) and `handle`
(verify, then parse, and say what to answer). They take the raw body bytes and the headers, so they fit
any web framework; the webhook-receiver-patterns skill shows how to get the raw body in Express,
FastAPI and ASP.NET Core. Unlike the shared-secret providers they also take your webhook id and a
`fetchCertificate(url)` function that returns the signing certificate as PEM text (the Node version may
be async).

| Folder | Code | Tests | Run |
|---|---|---|---|
| `node/` | `paypal.mjs` | `paypal.test.mjs` | `node --test` (Node.js 18+) |
| `python/` | `paypal_webhooks.py` | `test_paypal_webhooks.py` | `pip install -r requirements.txt`, then `python -m unittest` (Python 3.9+) |
| `csharp/` | `PayPalWebhooks.cs` | `PayPalWebhooksTests.cs` | `dotnet test` (.NET 10 SDK; the code itself needs .NET 9+) |

All three run every case in `fixtures/vectors.json`: requests signed by the openssl command line with an
RSA key and a self-signed certificate made for that run (by `tools/make-provider-vectors.py` in the
repository). The tests' `fetchCertificate` serves that certificate and throws for any other URL, so a
URL the host rule should have refused would show up as a failure. PayPal's docs print no worked example
to add. Everything in the vectors is a test value.

The Python module is `paypal_webhooks.py`, not `paypal.py`, so it cannot shadow PayPal's own package.

## The certificate URL

`PAYPAL-CERT-URL` arrives in the request, so it is attacker controlled until proven otherwise. A
certificate fetched from an attacker's host would let anyone sign. PayPal's docs do not state a host
rule, so the modules apply one of ours before fetching anything: https only, host `paypal.com` or a
subdomain of it, no userinfo, default port. The vectors include a valid signature whose certificate URL
is on another host, a look-alike host and plain http; all must answer 401 without a fetch. Cache
certificates by URL in your own code.

## Dependencies

- Node.js: none beyond the standard library (`crypto.X509Certificate`).
- Python: `cryptography` 50.0.2, because the standard library cannot parse certificates or verify RSA.
  CRC-32 is `zlib.crc32`.
- C#: none for `PayPalWebhooks.cs` (`X509Certificate2`, `RSA`). The test project uses
  `Microsoft.NET.Test.Sdk` 17.12.0, `xunit` 2.9.2 and `xunit.runner.visualstudio` 2.8.2.
- CRC-32 in Node.js and C# is a small table-based function in the file, because neither has one built in
  that matches (and a package for twenty lines is not worth the trust).

## What `handle` returns

| Request | Status | Also |
|---|---|---|
| Valid webhook | 200 | `type` = `event_type`, `id` = the body's `id` |
| Bad or missing signature, algorithm other than `SHA256withRSA`, or certificate URL refused | 401 | nothing fetched or parsed |
| Certificate could not be fetched | 500 | PayPal retries |
| Signed but not JSON, or no `event_type` or `id` | 400 | |

Deduplicate on `id` before doing the work.
