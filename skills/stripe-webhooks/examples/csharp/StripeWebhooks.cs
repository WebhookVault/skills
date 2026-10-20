// Verifies and reads Stripe webhook events. Framework-free: pass the raw body bytes and the headers;
// wire it into ASP.NET Core as shown in the webhook-receiver-patterns skill.
// .NET 9 or later, no packages.
//
// Stripe sends "Stripe-Signature: t=<timestamp>,v1=<hex>[,v1=<hex>...][,v0=<hex>]". Each v1 is
// HMAC-SHA256 over "<t>.<raw body>" with the endpoint's signing secret (the whole "whsec_..." string
// is the key). While a secret is being rolled there are two v1 values: any one may match. v0 is for
// test mode and is never accepted. Stripe's libraries refuse timestamps more than five minutes old.

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace StripeWebhooksExample;

/// <summary>What to answer, and what was received. Type and Id are set when Status is 200.</summary>
public sealed record StripeResult(int Status, string? Type = null, string? Id = null);

public static class StripeWebhooks
{
    public const int ToleranceSeconds = 300;

    static string? Header(IEnumerable<KeyValuePair<string, string>> headers, string name) =>
        headers.FirstOrDefault(h => string.Equals(h.Key, name, StringComparison.OrdinalIgnoreCase)).Value;

    /// <summary>True when the request carries a valid, fresh Stripe signature over these exact bytes.</summary>
    public static bool Verify(byte[] body, IEnumerable<KeyValuePair<string, string>> headers, string secret, long? now = null, int tolerance = ToleranceSeconds)
    {
        if (string.IsNullOrEmpty(secret)) throw new ArgumentException("The Stripe endpoint signing secret is required (read it from configuration).", nameof(secret));
        var value = Header(headers, "Stripe-Signature");
        if (value is null) return false;

        var timestamps = new List<string>();
        var candidates = new List<string>();
        foreach (var part in value.Split(','))
        {
            var eq = part.IndexOf('=');
            if (eq < 0) continue;
            var key = part[..eq];
            var val = part[(eq + 1)..];
            if (key == "t") timestamps.Add(val);
            else if (key == "v1") candidates.Add(val); // v0 and unknown keys are ignored
        }
        if (timestamps.Count != 1 || candidates.Count == 0) return false;
        var ts = timestamps[0];
        if (ts.Length is 0 or > 12 || !ts.All(char.IsAsciiDigit)) return false;
        var clock = now ?? DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        if (Math.Abs(clock - long.Parse(ts)) > tolerance) return false;

        var prefix = Encoding.UTF8.GetBytes($"{ts}.");
        var signed = new byte[prefix.Length + body.Length];
        prefix.CopyTo(signed, 0);
        body.CopyTo(signed, prefix.Length);
        var expected = Encoding.UTF8.GetBytes(Convert.ToHexStringLower(HMACSHA256.HashData(Encoding.UTF8.GetBytes(secret), signed)));
        // Check every candidate (no early exit) so the time taken does not say which one matched.
        var ok = false;
        foreach (var candidate in candidates)
            ok |= CryptographicOperations.FixedTimeEquals(Encoding.UTF8.GetBytes(candidate), expected);
        return ok;
    }

    /// <summary>
    /// Handles one request: verify, then parse. Type is the event name and Id the event id to
    /// deduplicate on. Answer 2xx quickly: queue the work and process it elsewhere.
    /// </summary>
    public static StripeResult Handle(byte[] body, IEnumerable<KeyValuePair<string, string>> headers, string secret, long? now = null, int tolerance = ToleranceSeconds)
    {
        if (!Verify(body, headers, secret, now, tolerance)) return new(401);

        JsonElement ev;
        try
        {
            ev = JsonDocument.Parse(body).RootElement;
        }
        catch (JsonException)
        {
            return new(400);
        }
        if (ev.ValueKind != JsonValueKind.Object) return new(400);
        var id = Str(ev, "id");
        var type = Str(ev, "type");
        return id is null || type is null ? new(400) : new(200, type, id);
    }

    static string? Str(JsonElement obj, string name) =>
        obj.TryGetProperty(name, out var v) && v.ValueKind == JsonValueKind.String ? v.GetString() : null;
}
