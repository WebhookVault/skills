// Runs against a real PostgreSQL: set WEBHOOK_TEST_DATABASE_URL (for example
// postgres://user:password@localhost:5432/scratch). Each run works in its own schema and drops it.

using Npgsql;
using Xunit;

namespace WebhookIdempotency;

public sealed class ProcessOnceTests : IAsyncLifetime
{
    private readonly string _schema = "idem_test_" + Convert.ToHexStringLower(System.Security.Cryptography.RandomNumberGenerator.GetBytes(6));
    private string _connectionString = null!;
    private NpgsqlDataSource _db = null!;

    /// <summary>postgres://user:password@host:port/db into an Npgsql connection string.</summary>
    private static string FromUrl(string url)
    {
        var uri = new Uri(url);
        var userInfo = uri.UserInfo.Split(':', 2);
        var b = new NpgsqlConnectionStringBuilder
        {
            Host = uri.Host,
            Port = uri.Port > 0 ? uri.Port : 5432,
            Database = uri.AbsolutePath.TrimStart('/'),
            Username = Uri.UnescapeDataString(userInfo[0]),
        };
        if (userInfo.Length > 1) b.Password = Uri.UnescapeDataString(userInfo[1]);
        return b.ConnectionString;
    }

    public async Task InitializeAsync()
    {
        var url = Environment.GetEnvironmentVariable("WEBHOOK_TEST_DATABASE_URL");
        if (string.IsNullOrEmpty(url)) throw new InvalidOperationException("Set WEBHOOK_TEST_DATABASE_URL to a PostgreSQL database these tests may create a schema in.");
        _connectionString = FromUrl(url);

        await using (var admin = NpgsqlDataSource.Create(_connectionString))
        await using (var create = admin.CreateCommand($"CREATE SCHEMA {_schema}"))
            await create.ExecuteNonQueryAsync();

        _db = NpgsqlDataSource.Create(new NpgsqlConnectionStringBuilder(_connectionString) { SearchPath = _schema, MaxPoolSize = 20 }.ConnectionString);
        await using var setup = _db.CreateCommand(ProcessOnce.SchemaSql + "CREATE TABLE orders (order_id text PRIMARY KEY, event_id text NOT NULL);");
        await setup.ExecuteNonQueryAsync();
    }

    public async Task DisposeAsync()
    {
        await _db.DisposeAsync();
        await using var admin = NpgsqlDataSource.Create(_connectionString);
        await using var drop = admin.CreateCommand($"DROP SCHEMA {_schema} CASCADE");
        await drop.ExecuteNonQueryAsync();
    }

    private static Func<NpgsqlConnection, NpgsqlTransaction, CancellationToken, Task> CreateOrder(string orderId, string eventId) =>
        async (conn, tx, ct) =>
        {
            await using var cmd = new NpgsqlCommand("INSERT INTO orders (order_id, event_id) VALUES ($1, $2)", conn, tx);
            cmd.Parameters.Add(new() { Value = orderId });
            cmd.Parameters.Add(new() { Value = eventId });
            await cmd.ExecuteNonQueryAsync(ct);
        };

    private async Task<long> Count(string sql)
    {
        await using var cmd = _db.CreateCommand(sql);
        return (long)(await cmd.ExecuteScalarAsync())!;
    }

    [Fact]
    public async Task the_first_delivery_is_processed_and_a_redelivery_is_a_duplicate()
    {
        Assert.Equal(Outcome.Processed, await ProcessOnce.RunAsync(_db, "shop", "evt_test_1", CreateOrder("ord_1", "evt_test_1")));
        Assert.Equal(Outcome.Duplicate, await ProcessOnce.RunAsync(_db, "shop", "evt_test_1", CreateOrder("ord_1b", "evt_test_1")));
        Assert.Equal(1, await Count("SELECT count(*) FROM orders WHERE event_id = 'evt_test_1'"));
    }

    [Fact]
    public async Task the_same_id_from_two_senders_is_two_events()
    {
        Assert.Equal(Outcome.Processed, await ProcessOnce.RunAsync(_db, "shop", "evt_test_2", CreateOrder("ord_2a", "evt_test_2")));
        Assert.Equal(Outcome.Processed, await ProcessOnce.RunAsync(_db, "billing", "evt_test_2", CreateOrder("ord_2b", "evt_test_2")));
    }

    [Fact]
    public async Task a_failed_handler_leaves_nothing_behind_and_the_retry_processes_it()
    {
        await Assert.ThrowsAsync<InvalidOperationException>(() => ProcessOnce.RunAsync(_db, "shop", "evt_test_3", async (conn, tx, ct) =>
        {
            await CreateOrder("ord_3", "evt_test_3")(conn, tx, ct);
            throw new InvalidOperationException("downstream failed");
        }));
        Assert.Equal(0, await Count("SELECT count(*) FROM orders WHERE order_id = 'ord_3'"));
        Assert.Equal(0, await Count("SELECT count(*) FROM webhook_events WHERE event_id = 'evt_test_3'"));
        Assert.Equal(Outcome.Processed, await ProcessOnce.RunAsync(_db, "shop", "evt_test_3", CreateOrder("ord_3", "evt_test_3")));
    }

    [Fact]
    public async Task ten_copies_arriving_at_once_run_the_handler_exactly_once()
    {
        var runs = 0;
        async Task Handler(NpgsqlConnection conn, NpgsqlTransaction tx, CancellationToken ct)
        {
            Interlocked.Increment(ref runs);
            await Task.Delay(50, ct);
            await CreateOrder("ord_4", "evt_test_4")(conn, tx, ct);
        }

        var results = await Task.WhenAll(Enumerable.Range(0, 10).Select(_ => Task.Run(() => ProcessOnce.RunAsync(_db, "shop", "evt_test_4", Handler))));
        Assert.Equal(1, results.Count(r => r == Outcome.Processed));
        Assert.Equal(9, results.Count(r => r == Outcome.Duplicate));
        Assert.Equal(1, runs);
        Assert.Equal(1, await Count("SELECT count(*) FROM orders WHERE order_id = 'ord_4'"));
    }

    [Fact]
    public async Task old_claims_can_be_forgotten()
    {
        await using (var cmd = _db.CreateCommand("INSERT INTO webhook_events (source, event_id, received_at) VALUES ('shop', 'evt_test_old', now() - interval '40 days'), ('shop', 'evt_test_new', now())"))
            await cmd.ExecuteNonQueryAsync();
        Assert.True(await ProcessOnce.ForgetOlderThanAsync(_db, 30) >= 1);
        Assert.Equal(0, await Count("SELECT count(*) FROM webhook_events WHERE event_id = 'evt_test_old'"));
        Assert.Equal(1, await Count("SELECT count(*) FROM webhook_events WHERE event_id = 'evt_test_new'"));
    }
}
