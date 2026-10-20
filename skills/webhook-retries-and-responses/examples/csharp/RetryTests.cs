using Xunit;

namespace WebhookRetries;

public class RetryTests
{
    // RFC 9110's own example of an HTTP-date.
    private const string RfcDate = "Wed, 21 Oct 2015 07:28:00 GMT";
    private static readonly long Now = DateTimeOffset.Parse("2015-10-21T07:27:00Z").ToUnixTimeMilliseconds();

    private sealed class Clock
    {
        public long T;
        public List<long> Waits { get; } = [];
        public Task Sleep(long ms) { Waits.Add(ms); T += ms; return Task.CompletedTask; }
    }

    private static Func<Task<SendResult>> Script(params object[] answers)
    {
        var i = 0;
        return () =>
        {
            var a = answers[Math.Min(i++, answers.Length - 1)];
            return a switch
            {
                "throw" => throw new HttpRequestException("connection reset"),
                int s => Task.FromResult(new SendResult(s)),
                SendResult r => Task.FromResult(r),
                _ => throw new ArgumentException("bad script"),
            };
        };
    }

    private static RetryPolicy Policy(Clock c, double random = 0.5, int maxAttempts = 8, long maxElapsedMs = 3_600_000)
        => new() { Random = () => random, Sleep = c.Sleep, Now = () => c.T, MaxAttempts = maxAttempts, MaxElapsedMs = maxElapsedMs };

    [Fact]
    public void only_statuses_that_can_succeed_later_are_retried()
    {
        foreach (var s in new[] { 408, 425, 429, 500, 502, 503, 504, 599 }) Assert.True(Retry.IsRetryableStatus(s), s.ToString());
        foreach (var s in new[] { 200, 301, 400, 401, 403, 404, 409, 410, 413, 422 }) Assert.False(Retry.IsRetryableStatus(s), s.ToString());
    }

    [Fact]
    public void backoff_doubles_under_the_cap_with_full_jitter()
    {
        Assert.Equal(999, Retry.BackoffDelay(0, 1000, 900_000, () => 0.999999));
        Assert.Equal(7999, Retry.BackoffDelay(3, 1000, 900_000, () => 0.999999));
        Assert.Equal(59_999, Retry.BackoffDelay(30, 1000, 60_000, () => 0.999999));
        Assert.Equal(0, Retry.BackoffDelay(5, 1000, 900_000, () => 0));
        Assert.Throws<ArgumentOutOfRangeException>(() => Retry.BackoffDelay(-1, 1000, 900_000, () => 0));
    }

    [Fact]
    public void retry_after_reads_seconds_and_the_http_date_only()
    {
        Assert.Equal(120_000, Retry.ParseRetryAfter("120", Now));
        Assert.Equal(0, Retry.ParseRetryAfter(" 0 ", Now));
        Assert.Equal(60_000, Retry.ParseRetryAfter(RfcDate, Now));
        Assert.Equal(0, Retry.ParseRetryAfter("Wed, 21 Oct 2015 07:26:00 GMT", Now));
        foreach (var bad in new[] { "-5", "1.5", "tomorrow", null }) Assert.Null(Retry.ParseRetryAfter(bad, Now));
    }

    [Fact]
    public async Task a_receiver_that_recovers_is_delivered_after_retries()
    {
        var c = new Clock();
        Assert.Equal(new DeliveryOutcome("delivered", 3, 200), await Retry.DeliverAsync(Script(503, "throw", 200), Policy(c)));
        Assert.Equal([500, 1000], c.Waits);
    }

    [Fact]
    public async Task a_permanent_answer_stops_at_once()
    {
        var c = new Clock();
        Assert.Equal(new DeliveryOutcome("rejected", 1, 400), await Retry.DeliverAsync(Script(400), Policy(c)));
        Assert.Empty(c.Waits);
    }

    [Fact]
    public async Task retry_after_is_honoured_instead_of_the_backoff()
    {
        var c = new Clock();
        var headers = new Dictionary<string, string> { ["retry-after"] = "7" };
        var r = await Retry.DeliverAsync(Script(new SendResult(429, headers), 200), Policy(c));
        Assert.Equal("delivered", r.Outcome);
        Assert.Equal([7000], c.Waits);
    }

    [Fact]
    public async Task the_attempt_budget_ends_in_a_dead_letter()
    {
        var c = new Clock();
        Assert.Equal(new DeliveryOutcome("dead_letter", 4, 500), await Retry.DeliverAsync(Script(500), Policy(c, random: 0, maxAttempts: 4)));
        Assert.Equal(3, c.Waits.Count);
    }

    [Fact]
    public async Task the_time_budget_ends_the_attempts_early()
    {
        var c = new Clock();
        var headers = new Dictionary<string, string> { ["retry-after"] = "7200" };
        Assert.Equal(new DeliveryOutcome("dead_letter", 1, 503), await Retry.DeliverAsync(Script(new SendResult(503, headers)), Policy(c)));
        Assert.Empty(c.Waits);
    }
}
