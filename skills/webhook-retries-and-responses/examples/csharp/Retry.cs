// Retrying a webhook delivery (or any call to a receiver) safely: exponential backoff with full
// jitter under a cap, retry only what can succeed later, honour Retry-After, give up after a budget
// and park the delivery as a dead letter. Base library only.
//
// Randomness, the clock and the wait are parameters so the behaviour is testable exactly.

using System.Globalization;
using System.Text.RegularExpressions;

namespace WebhookRetries;

public sealed record SendResult(int Status, IReadOnlyDictionary<string, string>? Headers = null);

public sealed record DeliveryOutcome(string Outcome, int Attempts, int? Status);

public sealed class RetryPolicy
{
    public int MaxAttempts { get; init; } = 8;
    public long BaseMs { get; init; } = 1000;
    public long CapMs { get; init; } = 15 * 60 * 1000;
    public long MaxElapsedMs { get; init; } = 60 * 60 * 1000;
    public Func<double> Random { get; init; } = System.Random.Shared.NextDouble;
    public Func<long, Task> Sleep { get; init; } = ms => Task.Delay(TimeSpan.FromMilliseconds(ms));
    public Func<long> Now { get; init; } = () => DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
}

public static partial class Retry
{
    /// <summary>Statuses worth retrying: the receiver may succeed later. Every other 4xx is permanent.</summary>
    public static bool IsRetryableStatus(int status) => status is 408 or 425 or 429 or (>= 500 and <= 599);

    /// <summary>Full jitter: a random delay in [0, min(cap, base * 2^attempt)) ms; attempt from 0.</summary>
    public static long BackoffDelay(int attempt, long baseMs, long capMs, Func<double> random)
    {
        ArgumentOutOfRangeException.ThrowIfNegative(attempt);
        var ceiling = Math.Min(capMs, baseMs * (1L << Math.Min(attempt, 30)));
        return (long)(random() * ceiling);
    }

    [GeneratedRegex(@"^[A-Za-z]{3}, \d{2} [A-Za-z]{3} \d{4} \d{2}:\d{2}:\d{2} GMT$")] private static partial Regex HttpDate();
    [GeneratedRegex(@"^\d+$")] private static partial Regex Digits();

    /// <summary>Retry-After (RFC 9110 10.2.3) in ms: delay-seconds or an HTTP-date. Null when absent or unreadable; never negative.</summary>
    public static long? ParseRetryAfter(string? value, long nowMs)
    {
        if (value is null) return null;
        var v = value.Trim();
        if (Digits().IsMatch(v)) return long.TryParse(v, out var seconds) ? seconds * 1000 : null;
        if (!HttpDate().IsMatch(v)) return null;
        if (!DateTimeOffset.TryParseExact(v, "r", CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal, out var at)) return null;
        return Math.Max(0, at.ToUnixTimeMilliseconds() - nowMs);
    }

    /// <summary>Sends with retries; an exception from send counts as a network error (retryable).</summary>
    public static async Task<DeliveryOutcome> DeliverAsync(Func<Task<SendResult>> send, RetryPolicy? policy = null)
    {
        policy ??= new RetryPolicy();
        var started = policy.Now();
        int? status = null;
        var made = 0;
        for (var attempt = 1; attempt <= policy.MaxAttempts; attempt++)
        {
            made = attempt;
            long? retryAfter = null;
            try
            {
                var res = await send();
                status = res.Status;
                if (res.Status is >= 200 and <= 299) return new("delivered", attempt, res.Status);
                if (!IsRetryableStatus(res.Status)) return new("rejected", attempt, res.Status);
                retryAfter = res.Headers is not null && res.Headers.TryGetValue("retry-after", out var ra) ? ParseRetryAfter(ra, policy.Now()) : null;
            }
            catch (Exception)
            {
                status = null;
            }
            if (attempt == policy.MaxAttempts) break;
            var wait = retryAfter ?? BackoffDelay(attempt - 1, policy.BaseMs, policy.CapMs, policy.Random);
            if (policy.Now() - started + wait > policy.MaxElapsedMs) break;
            await policy.Sleep(wait);
        }
        return new("dead_letter", made, status);
    }
}
