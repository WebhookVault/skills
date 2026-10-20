// Verifies and reads Resend webhooks. Framework-free: pass the raw body bytes and the headers; wire it
// into ASP.NET Core as shown in the webhook-receiver-patterns skill.
// .NET 9 or later, no packages.
//
// Resend delivers through Svix, which follows the Standard Webhooks scheme. The signing key is the
// base64 text after "whsec_" in the signing secret. The signed string is
// "<svix-id>.<svix-timestamp>.<raw body>"; HMAC-SHA256 with the decoded key, base64 encoded, goes in
// svix-signature as space-separated "v1,<signature>" entries (several while a secret is rotated).
// Svix's libraries reject a timestamp more than five minutes from local time.

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace ResendWebhooksExample;

/// <summary>What to answer, and what was received. Type and Id are set when Status is 200.</summary>
public sealed record ResendResult(int Status, string? Type = null, string? Id = null);

public static class ResendWebhooks
{
    public const int ToleranceSeconds = 300;

    static string? Header(IEnumerable<KeyValuePair<string, string>> headers, string name) =>
        headers.FirstOrDefault(h => string.Equals(h.Key, name, StringComparison.OrdinalIgnoreCase)).Value;

    static byte[] SigningKey(string secret)
    {
        var encoded = secret.StartsWith("whsec_", StringComparison.Ordinal) ? secret["whsec_".Length..] : secret;
        try
        {
            var key = Convert.FromBase64String(encoded);
            if (key.Length > 0) return key;
        }
        catch (FormatException)
        {
            // Falls through to the single error below.
        }
        throw new ArgumentException("The Resend signing secret is not valid base64 after the whsec_ prefix.", nameof(secret));
    }

    /// <summary>True when the request carries a valid, fresh Resend signature over these exact bytes.</summary>
    public static bool Verify(byte[] body, IEnumerable<KeyValuePair<string, string>> headers, string secret, long? now = null, int tolerance = ToleranceSeconds)
    {
        if (string.IsNullOrEmpty(secret)) throw new ArgumentException("The Resend signing secret is required (read it from configuration).", nameof(secret));
        var key = SigningKey(secret);
        var id = Header(headers, "svix-id");
        var ts = Header(headers, "svix-timestamp");
        var sigs = Header(headers, "svix-signature");
        if (string.IsNullOrEmpty(id) || sigs is null) return false;
        if (ts is null || ts.Length is 0 or > 12 || !ts.All(char.IsAsciiDigit)) return false;
        var clock = now ?? DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        if (Math.Abs(clock - long.Parse(ts)) > tolerance) return false;

        var prefix = Encoding.UTF8.GetBytes($"{id}.{ts}.");
        var signed = new byte[prefix.Length + body.Length];
        prefix.CopyTo(signed, 0);
        body.CopyTo(signed, prefix.Length);
        var expected = Encoding.UTF8.GetBytes(Convert.ToBase64String(HMACSHA256.HashData(key, signed)));

        // Only v1 entries count; other versions are ignored. Check every candidate, no early exit.
        var ok = false;
        foreach (var entry in sigs.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries))
        {
            var comma = entry.IndexOf(',');
            if (comma < 0 || entry[..comma] != "v1") continue;
            ok |= CryptographicOperations.FixedTimeEquals(Encoding.UTF8.GetBytes(entry[(comma + 1)..]), expected);
        }
        return ok;
    }

    /// <summary>
    /// Handles one request: verify, then parse. Id is the svix-id header, which stays the same across
    /// retries. Answer 2xx quickly and process elsewhere.
    /// </summary>
    public static ResendResult Handle(byte[] body, IEnumerable<KeyValuePair<string, string>> headers, string secret, long? now = null)
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
        var type = payload.TryGetProperty("type", out var t) && t.ValueKind == JsonValueKind.String ? t.GetString() : null;
        return type is null ? new(400) : new(200, type, Header(headers, "svix-id"));
    }
}
