# Examples: compare before write, on PostgreSQL

The same versioned upsert with tombstones in three languages, each tested against a **real
PostgreSQL**. Set `WEBHOOK_TEST_DATABASE_URL` to a database the tests may create a schema in (for
example `postgres://user:password@localhost:5432/scratch`); each run creates its own schema
(`order_test_...`) and drops it. The tests fail, rather than skip, when the variable is not set.

| Folder | Run the tests | Dependencies |
|---|---|---|
| `node/` | `npm ci`, then `node --test` (Node.js 18 or later) | `pg` 8.23.1 (`npm audit` reported 0 vulnerabilities on 2026-10-20) |
| `python/` | `python -m venv .venv`, install `requirements.txt`, then `python -m unittest test_apply.py` | `psycopg[binary]` 3.3.6 |
| `csharp/` | `dotnet test` (.NET 10 SDK) | `Npgsql` 10.0.3; xUnit for the tests |

Each suite checks the same six cases: in-order events apply; a late older event is stale; a
redelivery of the same version changes nothing; a delete leaves a tombstone a late update cannot
resurrect; a delete arriving before the create still wins; twenty events applied concurrently in
random order settle on the newest.

Versions are pinned to the releases current on 2026-10-20.
