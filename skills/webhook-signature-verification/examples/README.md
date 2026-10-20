# Examples: tested signature verification

One implementation per language, covering every family in the skill, each with tests.

| Folder | Run the tests | Dependencies |
|---|---|---|
| `node/` | `node --test` (Node.js 18 or later) | None |
| `python/` | `python -m venv .venv`, install `requirements.txt`, then `python -m unittest test_verify.py` | `cryptography` 50.0.2, for Ed25519 and ECDSA only |
| `csharp/` | `dotnet test` (.NET 10 SDK; the code needs .NET 9 or later) | `BouncyCastle.Cryptography` 2.7.0, for Ed25519 only; xUnit for the tests |

## How the tests know the code is right

A test that only checks code against itself proves nothing, so every implementation is checked
against two outside sources:

1. **`fixtures/vectors.json`**: requests for every family signed by the openssl command line, not by
   any of this code. `fixtures/make_vectors.py` rebuilds it (it needs openssl 3). Key-pair vectors use
   keys generated for that run; only the public halves are kept.
2. **`fixtures/published.json`**: the examples the senders publish themselves, copied exactly, each
   with its source page and the date it was read: GitHub's documentation, Slack's documentation, and
   the Standard Webhooks specification's library tests.

Each vector is then changed in the ways a verifier must reject: one byte of the body, the body parsed
and serialised again, the wrong secret, a timestamp outside the tolerance, a missing or malformed
header, a URL rebuilt behind a proxy, a header with two timestamps.

All secrets and keys here are test values.

## Dependencies are trust decisions

- **Node.js** uses only `node:crypto`.
- **Python** uses the standard library for every HMAC family. `cryptography` is the Python
  Cryptographic Authority's package; it is needed only because the standard library has no Ed25519
  or ECDSA.
- **C#** uses `System.Security.Cryptography` for HMAC and ECDSA. .NET has no Ed25519, so it uses
  `BouncyCastle.Cryptography`, the Legion of the Bouncy Castle's package.

Versions are pinned to the releases current on 2026-10-20. Update them deliberately, run the tests,
and record the new date here.
