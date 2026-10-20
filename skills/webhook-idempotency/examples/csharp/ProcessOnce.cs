// Process a webhook event at most once, with PostgreSQL and Npgsql.
//
// Insert-first: in ONE transaction, claim the event id with an INSERT against a unique key, do the
// business writes, and commit. A duplicate finds the id taken and stops. A failure rolls back both
// the claim and the business writes, so the sender's retry can process the event cleanly. Two copies
// arriving at the same moment cannot both run: the second INSERT waits on the first transaction's
// lock on the key, then sees the conflict.

using Npgsql;

namespace WebhookIdempotency;

public enum Outcome { Processed, Duplicate }

public static class ProcessOnce
{
    public const string SchemaSql = """
        CREATE TABLE IF NOT EXISTS webhook_events (
          source      text        NOT NULL,          -- which sender (ids are only unique per sender)
          event_id    text        NOT NULL,
          received_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (source, event_id)
        );
        """;

    /// <summary>
    /// Runs the handler in a transaction unless (source, eventId) was already processed. The handler
    /// must write with the connection and transaction it is given, so its writes commit or roll back
    /// together with the claim. Rethrows the handler's exception after rolling back.
    /// </summary>
    public static async Task<Outcome> RunAsync(NpgsqlDataSource db, string source, string eventId,
        Func<NpgsqlConnection, NpgsqlTransaction, CancellationToken, Task> handler, CancellationToken ct = default)
    {
        await using var conn = await db.OpenConnectionAsync(ct);
        await using var tx = await conn.BeginTransactionAsync(ct);

        await using (var claim = new NpgsqlCommand(
            "INSERT INTO webhook_events (source, event_id) VALUES ($1, $2) ON CONFLICT DO NOTHING", conn, tx))
        {
            claim.Parameters.Add(new() { Value = source });
            claim.Parameters.Add(new() { Value = eventId });
            if (await claim.ExecuteNonQueryAsync(ct) == 0)
            {
                await tx.RollbackAsync(ct);
                return Outcome.Duplicate;
            }
        }

        try
        {
            await handler(conn, tx, ct);
            await tx.CommitAsync(ct);
            return Outcome.Processed;
        }
        catch
        {
            await tx.RollbackAsync(CancellationToken.None);
            throw;
        }
    }

    /// <summary>Deletes claims older than the given days, so the table does not grow forever.</summary>
    public static async Task<int> ForgetOlderThanAsync(NpgsqlDataSource db, int days, CancellationToken ct = default)
    {
        await using var cmd = db.CreateCommand("DELETE FROM webhook_events WHERE received_at < now() - make_interval(days => $1)");
        cmd.Parameters.Add(new() { Value = days });
        return await cmd.ExecuteNonQueryAsync(ct);
    }
}
