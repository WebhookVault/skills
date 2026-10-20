"""Process a webhook event at most once, with PostgreSQL and psycopg 3.

Insert-first: in ONE transaction, claim the event id with an INSERT against a unique key, do the
business writes, and commit. A duplicate finds the id taken and stops. A failure rolls back both the
claim and the business writes, so the sender's retry can process the event cleanly. Two copies
arriving at the same moment cannot both run: the second INSERT waits on the first transaction's lock
on the key, then sees the conflict.
"""

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS webhook_events (
  source      text        NOT NULL,          -- which sender (ids are only unique per sender)
  event_id    text        NOT NULL,
  received_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (source, event_id)
);
"""


def process_once(conn, source: str, event_id: str, handler) -> str:
    """Runs handler(conn) in a transaction unless (source, event_id) was already processed.

    Returns "processed" or "duplicate". The handler must write through the same connection, so its
    writes commit or roll back together with the claim. Re-raises the handler's exception.

    Use an autocommit connection (psycopg.connect(..., autocommit=True)): then the transaction()
    block is the whole transaction. On a non-autocommit connection psycopg opens an outer
    transaction and this block becomes a savepoint, so nothing is committed until the caller commits.
    """
    with conn.transaction():
        claimed = conn.execute(
            "INSERT INTO webhook_events (source, event_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (source, event_id),
        ).rowcount
        if claimed == 0:
            return "duplicate"
        handler(conn)
    return "processed"


def forget_older_than(conn, days: int) -> int:
    """Deletes claims older than `days`, so the table does not grow forever. Returns the count."""
    with conn.transaction():
        return conn.execute(
            "DELETE FROM webhook_events WHERE received_at < now() - make_interval(days => %s)", (days,)
        ).rowcount
