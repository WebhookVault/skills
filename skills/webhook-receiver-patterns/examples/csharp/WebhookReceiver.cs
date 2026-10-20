// A webhook receiver skeleton for ASP.NET Core minimal APIs: cap the size, read the raw bytes,
// verify the signature, parse, deduplicate on the event id, acknowledge, and hand the work to a queue.
//
// The signature scheme here is a common one: header "Webhook-Signature: t=<unix>,v1=<hex>" with
// HMAC-SHA256 over "<t>.<raw body>". Swap Verify for your sender's scheme (see the
// webhook-signature-verification skill). The store and queue are interfaces; the in-memory store is
// for the example only. In production the store is a database table with a unique key.

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Routing;

namespace WebhookReceiver;

public interface IEventStore
{
    /// <summary>True only the first time an event id is seen.</summary>
    Task<bool> FirstTimeAsync(string eventId, CancellationToken ct);
}

public interface IEventQueue
{
    Task EnqueueAsync(JsonElement evt, CancellationToken ct);
}

public sealed class MemoryEventStore : IEventStore
{
    private readonly HashSet<string> _seen = [];
    private readonly Lock _gate = new();

    public Task<bool> FirstTimeAsync(string eventId, CancellationToken ct)
    {
        lock (_gate) return Task.FromResult(_seen.Add(eventId));
    }
}

public sealed record ReceiverOptions(string Secret, Func<long>? Now = null)
{
    public const int MaxBodyBytes = 256 * 1024;
    public const long ToleranceSeconds = 300;
}

public static partial class Webhooks
{
    [GeneratedRegex(@"^\d{1,12}$")] private static partial Regex Seconds();

    public static bool Verify(byte[] raw, string? header, string secret, long now)
    {
        if (header is null || string.IsNullOrEmpty(secret)) return false;
        var pairs = header.Split(',').Select(p =>
        {
            var i = p.IndexOf('=');
            return i < 0 ? (Key: p.Trim(), Value: "") : (Key: p[..i].Trim(), Value: p[(i + 1)..].Trim());
        }).ToList();
        var stamps = pairs.Where(p => p.Key == "t").Select(p => p.Value).ToList();
        if (stamps.Count != 1 || !Seconds().IsMatch(stamps[0])) return false;
        if (Math.Abs(now - long.Parse(stamps[0])) > ReceiverOptions.ToleranceSeconds) return false;

        byte[] signed = [.. Encoding.UTF8.GetBytes(stamps[0] + "."), .. raw];
        var expected = Encoding.UTF8.GetBytes(Convert.ToHexStringLower(HMACSHA256.HashData(Encoding.UTF8.GetBytes(secret), signed)));
        return pairs.Any(p => p.Key == "v1" && CryptographicOperations.FixedTimeEquals(Encoding.UTF8.GetBytes(p.Value), expected));
    }

    /// <summary>The raw body, or null when it is over the cap (counted while reading, whatever Content-Length says).</summary>
    private static async Task<byte[]?> ReadCappedAsync(HttpRequest request, CancellationToken ct)
    {
        if (request.ContentLength > ReceiverOptions.MaxBodyBytes) return null;
        using var buffer = new MemoryStream();
        var chunk = new byte[16 * 1024];
        int read;
        while ((read = await request.Body.ReadAsync(chunk, ct)) > 0)
        {
            if (buffer.Length + read > ReceiverOptions.MaxBodyBytes) return null;
            buffer.Write(chunk, 0, read);
        }
        return buffer.ToArray();
    }

    /// <summary>Maps POST /webhooks. The body is never bound to a model: it is read as bytes and verified first.</summary>
    public static IEndpointRouteBuilder MapWebhooks(this IEndpointRouteBuilder routes, ReceiverOptions options)
    {
        if (string.IsNullOrEmpty(options.Secret)) throw new ArgumentException("A signing secret is required (read it from configuration).");

        routes.MapPost("/webhooks", async (HttpRequest request, IEventStore store, IEventQueue queue, CancellationToken ct) =>
        {
            var raw = await ReadCappedAsync(request, ct);
            if (raw is null) return Results.Json(new { error = "too_large" }, statusCode: 413);

            // 1. Authenticity before anything else: an unverified request must not touch state.
            var now = options.Now?.Invoke() ?? DateTimeOffset.UtcNow.ToUnixTimeSeconds();
            if (!Verify(raw, request.Headers["Webhook-Signature"].FirstOrDefault(), options.Secret, now))
                return Results.Json(new { error = "invalid_signature" }, statusCode: 401);

            // 2. Parse only after verifying, from the same bytes.
            JsonElement evt;
            try { evt = JsonDocument.Parse(raw).RootElement.Clone(); }
            catch (JsonException) { return Results.Json(new { error = "invalid_json" }, statusCode: 400); }
            if (evt.ValueKind != JsonValueKind.Object || !evt.TryGetProperty("id", out var idProp)
                || idProp.ValueKind != JsonValueKind.String || idProp.GetString() is not { Length: > 0 and <= 200 } id)
                return Results.Json(new { error = "missing_event_id" }, statusCode: 400);

            // 3. Deduplicate: the sender retries, so the same event can arrive more than once.
            if (!await store.FirstTimeAsync(id, ct)) return Results.Json(new { received = true, duplicate = true });

            // 4. Acknowledge fast; the work happens elsewhere. A failed hand-off answers 500 so the
            //    sender retries (and the store must forget the id; see the webhook-idempotency skill).
            try { await queue.EnqueueAsync(evt, ct); }
            catch (Exception) when (!ct.IsCancellationRequested) { return Results.Json(new { error = "try_again" }, statusCode: 500); }
            return Results.Json(new { received = true });
        });
        return routes;
    }
}
