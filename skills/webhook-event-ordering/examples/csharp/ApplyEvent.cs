// Apply webhook events that may arrive out of order, with PostgreSQL and Npgsql.
//
// Compare before write: every event carries a version (a sequence number or an update timestamp
// from the sender). One statement upserts the row only when the incoming version is newer, so a late
// older event can never overwrite newer state, and concurrent events settle on the newest. Deletes
// leave a tombstone (deleted = true, with its version) so a late update cannot resurrect a deleted
// record.

using Npgsql;

namespace WebhookOrdering;

public sealed record CustomerEvent(string CustomerId, long Version, string Type, string? Email = null, string? Plan = null);

public static class ApplyEvent
{
    public const string SchemaSql = """
        CREATE TABLE IF NOT EXISTS customers (
          customer_id text    PRIMARY KEY,
          email       text,
          plan        text,
          deleted     boolean NOT NULL DEFAULT false,
          version     bigint  NOT NULL          -- the sender's version of this record
        );
        """;

    private const string UpsertSql = """
        INSERT INTO customers (customer_id, email, plan, deleted, version)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (customer_id) DO UPDATE
          SET email = EXCLUDED.email, plan = EXCLUDED.plan, deleted = EXCLUDED.deleted, version = EXCLUDED.version
          WHERE customers.version < EXCLUDED.version
        """;

    /// <summary>Applies an "upserted" or "deleted" event. Returns true when it changed the row, false when stale.</summary>
    public static async Task<bool> RunAsync(NpgsqlDataSource db, CustomerEvent e, CancellationToken ct = default)
    {
        ArgumentException.ThrowIfNullOrEmpty(e.CustomerId);
        var deleted = e.Type == "deleted";
        await using var cmd = db.CreateCommand(UpsertSql);
        cmd.Parameters.Add(new() { Value = e.CustomerId });
        cmd.Parameters.Add(new() { Value = deleted ? DBNull.Value : (object?)e.Email ?? DBNull.Value });
        cmd.Parameters.Add(new() { Value = deleted ? DBNull.Value : (object?)e.Plan ?? DBNull.Value });
        cmd.Parameters.Add(new() { Value = deleted });
        cmd.Parameters.Add(new() { Value = e.Version });
        return await cmd.ExecuteNonQueryAsync(ct) == 1;
    }
}
