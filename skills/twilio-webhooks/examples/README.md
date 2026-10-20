# Twilio examples

One module per language with the same two functions: `verify` (the signature alone) and `handle`
(verify, then read, and say what to answer). They take the raw body bytes, the headers and the public
URL Twilio called, so they fit any web framework; the webhook-receiver-patterns skill shows how to get
the raw body in Express, FastAPI and ASP.NET Core.

| Folder | Code | Tests | Run |
|---|---|---|---|
| `node/` | `twilio.mjs` | `twilio.test.mjs` | `node --test` (Node.js 18+) |
| `python/` | `twilio_webhooks.py` | `test_twilio_webhooks.py` | `python -m unittest` (Python 3.9+) |
| `csharp/` | `TwilioWebhooks.cs` | `TwilioWebhooksTests.cs` | `dotnet test` (.NET 10 SDK; the code itself needs .NET 9+) |

All three run every case in `fixtures/vectors.json`: requests signed by the
openssl command line (made by `tools/make-provider-vectors.py` in the repository), plus the worked
example from Twilio's "Webhooks security" page. All tokens in them are test values.

The Python module is `twilio_webhooks.py`, not `twilio.py`, so it cannot shadow Twilio's own package.

## Dependencies

- Node.js and Python: none beyond the standard library.
- C#: none for `TwilioWebhooks.cs`. The test project uses `Microsoft.NET.Test.Sdk` 17.12.0, `xunit`
  2.9.2 and `xunit.runner.visualstudio` 2.8.2 to run the tests, nothing else.

## What `handle` returns

| Request | Status | Also |
|---|---|---|
| Valid form or JSON callback | 200 | `type` = `MessageStatus`, `SmsStatus` or `CallStatus`; `id` = `MessageSid`, `SmsSid` or `CallSid`; `idempotencyToken` when Twilio retried |
| Bad or missing signature, wrong URL, JSON body not matching `bodySHA256` | 401 | nothing read |
| Signed JSON that does not parse | 400 | |

Twilio has no event id: deduplicate on `idempotencyToken` when present, otherwise on `id` plus `type`.
For an incoming message or call, answer with TwiML instead of an empty 200.
