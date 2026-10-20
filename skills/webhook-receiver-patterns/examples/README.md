# Examples: tested receiver skeletons

The same receiver in three frameworks. Each test signs its requests with the openssl command line
(openssl 3 on PATH; on Windows run them from Git Bash, or set `OPENSSL` for the C# tests), so the
receiver's verification is checked against an independent implementation.

| Folder | Run the tests | Dependencies |
|---|---|---|
| `node/` | `npm ci`, then `node --test` (Node.js 18 or later) | Express 5.3.0 (`package-lock.json` pins the tree; `npm audit` reported 0 vulnerabilities on 2026-10-20) |
| `python/` | `python -m venv .venv`, install `requirements.txt`, then `python -m unittest test_app.py` | FastAPI 0.151.0; httpx 0.28.1 for FastAPI's test client |
| `csharp/` | `dotnet test` (.NET 10 SDK) | ASP.NET Core (shared framework); Microsoft.AspNetCore.TestHost 10.0.13 and xUnit for the tests |

Each suite checks the same eleven cases: a signed event is acknowledged and queued once; a duplicate
is acknowledged and not queued again; a wrong signature is 401 and queues nothing; an unverified
request does not use up the event id; a stale timestamp is 401; a missing signature header is 401; a
signed body that is not JSON is 400; a signed event without an id is 400; a body over the limit is
413; a failed hand-off is 500; re-formatted JSON fails verification.

The signing secret in the tests is a test value. To run a receiver yourself, set `WEBHOOK_SECRET` to
a test secret: `node server.mjs` (port 3000), or `uvicorn app:app` with FastAPI.

The dedupe store and queue are in memory for the examples. In production the store is a database
table with a unique key on the event id and the queue is a real queue or a jobs table.

Versions are pinned to the releases current on 2026-10-20. Update them deliberately, run the tests
and `npm audit`, and record the new date here.
