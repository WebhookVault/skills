// Apply webhook events that may arrive out of order, with PostgreSQL and the `pg` driver.
//
// Compare before write: every event carries a version (a sequence number or an update timestamp
// from the sender). One statement upserts the row only when the incoming version is newer, so a late
// older event can never overwrite newer state, and two concurrent events settle on the newest.
// Deletes leave a tombstone (deleted = true, with its version) so a late update cannot resurrect a
// deleted record.

export const SCHEMA_SQL = `
CREATE TABLE IF NOT EXISTS customers (
  customer_id text    PRIMARY KEY,
  email       text,
  plan        text,
  deleted     boolean NOT NULL DEFAULT false,
  version     bigint  NOT NULL          -- the sender's version of this record
);`;

/**
 * Applies an "upserted" or "deleted" event. Returns "applied" when it changed the row, "stale" when
 * a newer (or the same) version was already stored. Atomic in one statement.
 */
export async function applyEvent(db, event) {
  const { customerId, version, type } = event;
  if (typeof customerId !== "string" || !Number.isSafeInteger(version)) throw new TypeError("customerId and an integer version are required");
  const deleted = type === "deleted";
  const res = await db.query(
    `INSERT INTO customers (customer_id, email, plan, deleted, version)
     VALUES ($1, $2, $3, $4, $5)
     ON CONFLICT (customer_id) DO UPDATE
       SET email = EXCLUDED.email, plan = EXCLUDED.plan, deleted = EXCLUDED.deleted, version = EXCLUDED.version
       WHERE customers.version < EXCLUDED.version`,
    [customerId, deleted ? null : event.email ?? null, deleted ? null : event.plan ?? null, deleted, version],
  );
  return res.rowCount === 1 ? "applied" : "stale";
}
