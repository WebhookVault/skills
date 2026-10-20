"""Apply webhook events that may arrive out of order, with PostgreSQL and psycopg 3.

Compare before write: every event carries a version (a sequence number or an update timestamp from
the sender). One statement upserts the row only when the incoming version is newer, so a late older
event can never overwrite newer state, and concurrent events settle on the newest. Deletes leave a
tombstone (deleted = true, with its version) so a late update cannot resurrect a deleted record.
"""

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS customers (
  customer_id text    PRIMARY KEY,
  email       text,
  plan        text,
  deleted     boolean NOT NULL DEFAULT false,
  version     bigint  NOT NULL          -- the sender's version of this record
);
"""

UPSERT_SQL = """
INSERT INTO customers (customer_id, email, plan, deleted, version)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (customer_id) DO UPDATE
  SET email = EXCLUDED.email, plan = EXCLUDED.plan, deleted = EXCLUDED.deleted, version = EXCLUDED.version
  WHERE customers.version < EXCLUDED.version
"""


def apply_event(conn, event: dict) -> str:
    """Applies an "upserted" or "deleted" event. Returns "applied" or "stale". One atomic statement;
    use an autocommit connection or commit afterwards."""
    customer_id, version = event.get("customerId"), event.get("version")
    if not isinstance(customer_id, str) or not isinstance(version, int) or isinstance(version, bool):
        raise TypeError("customerId and an integer version are required")
    deleted = event.get("type") == "deleted"
    cur = conn.execute(UPSERT_SQL, (customer_id, None if deleted else event.get("email"),
                                    None if deleted else event.get("plan"), deleted, version))
    return "applied" if cur.rowcount == 1 else "stale"
