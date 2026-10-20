// Verifies and reads Paddle Billing notifications. Framework-free: pass the raw body bytes and the
// headers; wire it into ASP.NET Core as shown in the webhook-receiver-patterns skill.
// .NET 9 or later, no packages.
//
// Paddle sends "Paddle-Signature: ts=<unix seconds>;h1=<hex>" (several h1 values while a secret is
// being rotated). Each h1 is HMAC-SHA256, keyed with the notification destination's secret key string,
// over "<ts>:<raw body>". Paddle's guidance is to reject a timestamp more than five seconds from
// local time, which is tight: keep the server clock synchronised.

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace PaddleWebhooksExample;

/// <summary>What to answer, and what was received. Type and Id are set when Status is 200.</summary>
public sealed record PaddleResult(int Status, string? Type = null, string? Id = null);

public static class PaddleWebhooks
{
    public const int ToleranceSeconds = 5;

    static string? Header(IEnumerable<KeyValuePair<string, string>> headers, string name) =>
        headers.FirstOrDefault(h => string.Equals(h.Key, name, StringComparison.OrdinalIgnoreCase)).Value;

    /// <summary>True when the request carries a valid, fresh Paddle signature over these exact bytes.</summary>
    public static bool Verify(byte[] body, IEnumerable<KeyValuePair<string, string>> headers, string secret, long? now = null, int tolerance = ToleranceSeconds)
    {
        if (string.IsNullOrEmpty(secret)) throw new ArgumentException("The Paddle notification secret key is required (read it from configuration).", nameof(secret));
        var value = Header(headers, "Paddle-Signature");
        if (value is null) return false;

        var timestamps = new List<string>();
        var signatures = new List<string>();
        foreach (var part in value.Split(';'))
        {
            var at = part.IndexOf('=');
            if (at < 0) continue;
            var key = part[..at].Trim();
            var val = part[(at + 1)..].Trim();
            if (key == "ts") timestamps.Add(val);
            else if (key == "h1") signatures.Add(val);
        }
        if (timestamps.Count != 1 || signatures.Count == 0) return false;
        var ts = timestamps[0];
        if (ts.Length is 0 or > 12 || !ts.All(char.IsAsciiDigit)) return false;
        var clock = now ?? DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        if (Math.Abs(clock - long.Parse(ts)) > tolerance) return false;

        var prefix = Encoding.UTF8.GetBytes($"{ts}:");
        var signed = new byte[prefix.Length + body.Length];
        prefix.CopyTo(signed, 0);
        body.CopyTo(signed, prefix.Length);
        var expected = Encoding.UTF8.GetBytes(Convert.ToHexStringLower(HMACSHA256.HashData(Encoding.UTF8.GetBytes(secret), signed)));
        // Check every candidate (no early exit on the first match) so timing does not reveal which matched.
        var ok = false;
        foreach (var s in signatures)
            ok |= CryptographicOperations.FixedTimeEquals(Encoding.UTF8.GetBytes(s.ToLowerInvariant()), expected);
        return ok;
    }

    /// <summary>
    /// Handles one request: verify, then parse. Type is Paddle's event_type and Id its event_id (the
    /// id to deduplicate on). Answer 200 quickly and process elsewhere: Paddle retries on anything else.
    /// </summary>
    public static PaddleResult Handle(byte[] body, IEnumerable<KeyValuePair<string, string>> headers, string secret, long? now = null)
    {
        if (!Verify(body, headers, secret, now)) return new(401);

        JsonElement payload;
        try
        {
            payload = JsonDocument.Parse(body).RootElement;
        }
        catch (JsonException)
        {
            return new(400);
        }
        if (payload.ValueKind != JsonValueKind.Object) return new(400);
        var type = Str(payload, "event_type");
        var id = Str(payload, "event_id");
        return type is null || id is null ? new(400) : new(200, type, id);
    }

    static string? Str(JsonElement obj, string name) =>
        obj.TryGetProperty(name, out var v) && v.ValueKind == JsonValueKind.String ? v.GetString() : null;
}
