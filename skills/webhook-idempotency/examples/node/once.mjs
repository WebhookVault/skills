// Process a webhook event at most once, with PostgreSQL and the `pg` driver.
//
// Insert-first: in ONE transaction, claim the event id with an INSERT against a unique key, do the
// business writes, and commit. A duplicate finds the id taken and stops. A failure rolls back both
// the claim and the business writes, so the sender's retry can process the event cleanly. Two
// copies arriving at the same moment cannot both run: the second INSERT waits on the first
// transaction's lock on the key, then sees the conflict.

export const SCHEMA_SQL = `
CREATE TABLE IF NOT EXISTS webhook_events (
  source      text        NOT NULL,          -- which sender (ids are only unique per sender)
  event_id    text        NOT NULL,
  received_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (source, event_id)
);`;

/**
 * Runs `handler(client, event)` inside a transaction unless (source, eventId) was already
 * processed. Returns "processed" or "duplicate". The handler must do its writes with the client it
 * is given, so they commit or roll back together with the claim. Throws when the handler throws.
 */
export async function processOnce(pool, source, eventId, handler) {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const claim = await client.query(
      "INSERT INTO webhook_events (source, event_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
      [source, eventId],
    );
    if (claim.rowCount === 0) {
      await client.query("ROLLBACK");
      return "duplicate";
    }
    await handler(client);
    await client.query("COMMIT");
    return "processed";
  } catch (err) {
    await client.query("ROLLBACK").catch(() => {});
    throw err;
  } finally {
    client.release();
  }
}

/** Deletes claims older than `days`, so the table does not grow forever. Returns the count. */
export async function forgetOlderThan(pool, days) {
  const res = await pool.query("DELETE FROM webhook_events WHERE received_at < now() - make_interval(days => $1)", [days]);
  return res.rowCount;
}
