# Examples: process an event at most once, on PostgreSQL

The same insert-first claim in three languages, each tested against a **real PostgreSQL**: the
behaviour that matters (a unique key, a transaction, row locks under concurrency) lives in the
database, so a mock would test nothing.

Set `WEBHOOK_TEST_DATABASE_URL` to a database the tests may create a schema in, for example
`postgres://user:password@localhost:5432/scratch`. Each run creates its own schema (`idem_test_...`)
and drops it at the end. The tests fail, rather than skip, when the variable is not set.

| Folder | Run the tests | Dependencies |
|---|---|---|
| `node/` | `npm ci`, then `node --test` (Node.js 18 or later) | `pg` 8.23.1 (`package-lock.json` pins the tree; `npm audit` reported 0 vulnerabilities on 2026-10-20) |
| `python/` | `python -m venv .venv`, install `requirements.txt`, then `python -m unittest test_once.py` | `psycopg[binary]` 3.3.6 (bundles libpq) |
| `csharp/` | `dotnet test` (.NET 10 SDK) | `Npgsql` 10.0.3; xUnit for the tests |

Each suite checks the same five cases: a redelivery is a duplicate; the same id from two senders is
two events; a failed handler leaves no claim and no business row, and the retry succeeds; ten copies
arriving at once run the handler exactly once; claims older than a cut-off are deleted.

Versions are pinned to the releases current on 2026-10-20. Update them deliberately, run the tests
and `npm audit`, and record the new date here.
