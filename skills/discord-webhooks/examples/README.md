# Discord examples

One module per language with `verify` (the signature alone) and two handlers, because Discord has two
ways to call you and they answer differently: `handleEvent` for Webhook Events and `handleInteraction`
for the Interactions endpoint. They take the raw body bytes and the headers, so they fit any web
framework; the webhook-receiver-patterns skill shows how to get the raw body in Express, FastAPI and
ASP.NET Core. The Python functions are `handle_event` and `handle_interaction`; the C# ones are
`HandleEvent` and `HandleInteraction`.

| Folder | Code | Tests | Run |
|---|---|---|---|
| `node/` | `discord.mjs` | `discord.test.mjs` | `node --test` (Node.js 18+) |
| `python/` | `discord_webhooks.py` | `test_discord_webhooks.py` | `pip install -r requirements.txt`, then `python -m unittest` (Python 3.9+) |
| `csharp/` | `DiscordWebhooks.cs` | `DiscordWebhooksTests.cs` | `dotnet test` (.NET 10 SDK; the code itself needs .NET 9+) |

All three run every case in `fixtures/vectors.json`: requests signed by the openssl command line with an
Ed25519 key made for that run (by `tools/make-provider-vectors.py` in the repository). Only the public
half of the key is kept. Each case says which mechanism it belongs to. Discord's docs print no worked
example to add.

The Python module is `discord_webhooks.py`, not `discord.py`, so it cannot shadow the `discord.py`
library.

## Dependencies

- Node.js: none beyond the standard library (`crypto.verify` checks Ed25519).
- Python: `cryptography` 50.0.2, because the standard library has no Ed25519.
- C#: `BouncyCastle.Cryptography` 2.7.0 for `DiscordWebhooks.cs`, because .NET does not include Ed25519.
  The test project also uses `Microsoft.NET.Test.Sdk` 17.12.0, `xunit` 2.9.2 and
  `xunit.runner.visualstudio` 2.8.2.

## What the handlers return

| Request | Status | Also |
|---|---|---|
| Events: PING (outer `type` 0) | 204 | `type` = `PING` |
| Events: event (outer `type` 1) | 204 | `type` = `event.type` |
| Interactions: PING (`type` 1) | 200 | `reply` = `{"type":1}`, to send back as the body; `id` = the interaction id |
| Interactions: anything else | 200 | `type` = the integer interaction type, `id`, `reply` = null |
| Bad or missing signature, or a key or signature that is not hex | 401 | nothing parsed |
| Signed but not JSON, or missing the fields above | 400 | |

Discord checks your endpoint when you save its URL by sending a PING and also a request with an invalid
signature, and expects 401 for the second: a handler that does not verify cannot be saved. In C# the
interaction `type` comes back as text (`"2"`), as the result record holds strings.
