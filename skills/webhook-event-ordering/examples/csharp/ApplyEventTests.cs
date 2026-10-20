// Runs against a real PostgreSQL: set WEBHOOK_TEST_DATABASE_URL. Each run works in its own schema.

using Npgsql;
using Xunit;

namespace WebhookOrdering;

public sealed class ApplyEventTests : IAsyncLifetime
{
    private readonly string _schema = "order_test_" + Convert.ToHexStringLower(System.Security.Cryptography.RandomNumberGenerator.GetBytes(6));
    private string _cs = null!;
    private NpgsqlDataSource _db = null!;

    private static string FromUrl(string url)
    {
        var uri = new Uri(url);
        var userInfo = uri.UserInfo.Split(':', 2);
        var b = new NpgsqlConnectionStringBuilder
        {
            Host = uri.Host, Port = uri.Port > 0 ? uri.Port : 5432,
            Database = uri.AbsolutePath.TrimStart('/'), Username = Uri.UnescapeDataString(userInfo[0]),
        };
        if (userInfo.Length > 1) b.Password = Uri.UnescapeDataString(userInfo[1]);
        return b.ConnectionString;
    }

    public async Task InitializeAsync()
    {
        var url = Environment.GetEnvironmentVariable("WEBHOOK_TEST_DATABASE_URL");
        if (string.IsNullOrEmpty(url)) throw new InvalidOperationException("Set WEBHOOK_TEST_DATABASE_URL to a PostgreSQL database these tests may create a schema in.");
        _cs = FromUrl(url);
        await using (var admin = NpgsqlDataSource.Create(_cs))
        await using (var c = admin.CreateCommand($"CREATE SCHEMA {_schema}")) await c.ExecuteNonQueryAsync();
        _db = NpgsqlDataSource.Create(new NpgsqlConnectionStringBuilder(_cs) { SearchPath = _schema, MaxPoolSize = 30 }.ConnectionString);
        await using var setup = _db.CreateCommand(ApplyEvent.SchemaSql);
        await setup.ExecuteNonQueryAsync();
    }

    public async Task DisposeAsync()
    {
        await _db.DisposeAsync();
        await using var admin = NpgsqlDataSource.Create(_cs);
        await using var drop = admin.CreateCommand($"DROP SCHEMA {_schema} CASCADE");
        await drop.ExecuteNonQueryAsync();
    }

    private async Task<(string? Email, string? Plan, bool Deleted, long Version)> Row(string id)
    {
        await using var cmd = _db.CreateCommand("SELECT email, plan, deleted, version FROM customers WHERE customer_id = $1");
        cmd.Parameters.Add(new() { Value = id });
        await using var r = await cmd.ExecuteReaderAsync();
        Assert.True(await r.ReadAsync());
        return (r.IsDBNull(0) ? null : r.GetString(0), r.IsDBNull(1) ? null : r.GetString(1), r.GetBoolean(2), r.GetInt64(3));
    }

    private static CustomerEvent Upsert(string id, long v, string plan, string email = "x@example.test") => new(id, v, "upserted", email, plan);

    [Fact]
    public async Task events_in_order_are_all_applied()
    {
        Assert.True(await ApplyEvent.RunAsync(_db, Upsert("c1", 1, "free")));
        Assert.True(await ApplyEvent.RunAsync(_db, Upsert("c1", 2, "pro")));
        Assert.Equal("pro", (await Row("c1")).Plan);
    }

    [Fact]
    public async Task an_older_event_arriving_late_does_not_overwrite_newer_state()
    {
        await ApplyEvent.RunAsync(_db, Upsert("c2", 5, "pro", "new@example.test"));
        Assert.False(await ApplyEvent.RunAsync(_db, Upsert("c2", 3, "free", "old@example.test")));
        Assert.Equal(("new@example.test", "pro", false, 5L), await Row("c2"));
    }

    [Fact]
    public async Task a_redelivery_of_the_same_version_changes_nothing()
    {
        await ApplyEvent.RunAsync(_db, Upsert("c3", 1, "free"));
        Assert.False(await ApplyEvent.RunAsync(_db, Upsert("c3", 1, "free")));
    }

    [Fact]
    public async Task a_delete_leaves_a_tombstone_a_late_update_cannot_resurrect()
    {
        await ApplyEvent.RunAsync(_db, Upsert("c4", 1, "pro"));
        Assert.True(await ApplyEvent.RunAsync(_db, new("c4", 3, "deleted")));
        Assert.False(await ApplyEvent.RunAsync(_db, Upsert("c4", 2, "pro")));
        Assert.True((await Row("c4")).Deleted);
    }

    [Fact]
    public async Task a_delete_arriving_before_the_create_still_wins()
    {
        Assert.True(await ApplyEvent.RunAsync(_db, new("c5", 2, "deleted")));
        Assert.False(await ApplyEvent.RunAsync(_db, Upsert("c5", 1, "free")));
        Assert.True((await Row("c5")).Deleted);
    }

    [Fact]
    public async Task twenty_events_applied_concurrently_in_random_order_settle_on_the_newest()
    {
        var events = Enumerable.Range(1, 20).Select(i => Upsert("c6", i, $"plan-{i}", "c6@example.test")).OrderBy(_ => Random.Shared.Next()).ToList();
        await Task.WhenAll(events.Select(e => Task.Run(() => ApplyEvent.RunAsync(_db, e))));
        Assert.Equal(("c6@example.test", "plan-20", false, 20L), await Row("c6"));
    }
}
