// Verifies and reads Slack Events API and interactivity requests. Framework-free: pass the raw body
// bytes and the headers; wire it into ASP.NET Core as shown in the webhook-receiver-patterns skill.
// .NET 9 or later, no packages.
//
// Slack signs "v0:<X-Slack-Request-Timestamp>:<raw body>" with HMAC-SHA256 and the app's signing
// secret, hex encoded and prefixed "v0=", in X-Slack-Signature. Slack's own example rejects a
// timestamp more than five minutes from local time.

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace SlackWebhooksExample;

/// <summary>What to answer, and what was received. Type and Id are set when Status is 200.</summary>
public sealed record SlackResult(int Status, string? Type = null, string? Id = null, string? Reply = null);

public static class SlackWebhooks
{
    public const int ToleranceSeconds = 300;

    static string? Header(IEnumerable<KeyValuePair<string, string>> headers, string name) =>
        headers.FirstOrDefault(h => string.Equals(h.Key, name, StringComparison.OrdinalIgnoreCase)).Value;

    /// <summary>True when the request carries a valid, fresh Slack signature over these exact bytes.</summary>
    public static bool Verify(byte[] body, IEnumerable<KeyValuePair<string, string>> headers, string secret, long? now = null, int tolerance = ToleranceSeconds)
    {
        if (string.IsNullOrEmpty(secret)) throw new ArgumentException("The Slack signing secret is required (read it from configuration).", nameof(secret));
        var ts = Header(headers, "X-Slack-Request-Timestamp");
        var sig = Header(headers, "X-Slack-Signature");
        if (ts is null || sig is null || ts.Length is 0 or > 12 || !ts.All(char.IsAsciiDigit)) return false;
        var clock = now ?? DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        if (Math.Abs(clock - long.Parse(ts)) > tolerance) return false;

        var prefix = Encoding.UTF8.GetBytes($"v0:{ts}:");
        var signed = new byte[prefix.Length + body.Length];
        prefix.CopyTo(signed, 0);
        body.CopyTo(signed, prefix.Length);
        var expected = "v0=" + Convert.ToHexStringLower(HMACSHA256.HashData(Encoding.UTF8.GetBytes(secret), signed));
        return CryptographicOperations.FixedTimeEquals(Encoding.UTF8.GetBytes(sig), Encoding.UTF8.GetBytes(expected));
    }

    /// <summary>
    /// Handles one request: verify, then parse. Id is Slack's event_id (null for interactions, which
    /// have none); Reply is set for url_verification. Answer within three seconds: queue the work.
    /// </summary>
    public static SlackResult Handle(byte[] body, IEnumerable<KeyValuePair<string, string>> headers, string secret, long? now = null)
    {
        if (!Verify(body, headers, secret, now)) return new(401);

        JsonElement payload;
        try
        {
            var contentType = Header(headers, "Content-Type") ?? "";
            if (contentType.StartsWith("application/x-www-form-urlencoded", StringComparison.OrdinalIgnoreCase))
            {
                // Interactivity: one form field, "payload", holding JSON.
                var field = Form.Parse(Encoding.UTF8.GetString(body)).FirstOrDefault(p => p.Key == "payload").Value;
                if (field is null) return new(400);
                payload = JsonDocument.Parse(field).RootElement;
            }
            else
            {
                payload = JsonDocument.Parse(body).RootElement;
            }
        }
        catch (JsonException)
        {
            return new(400);
        }
        if (payload.ValueKind != JsonValueKind.Object) return new(400);

        var kind = Str(payload, "type");
        if (kind == "url_verification")
        {
            // Answered only after the signature checked out, so nobody else can register this URL.
            var challenge = Str(payload, "challenge");
            return challenge is null ? new(400) : new(200, "url_verification", null, challenge);
        }
        if (kind == "event_callback")
        {
            var type = payload.TryGetProperty("event", out var ev) && ev.ValueKind == JsonValueKind.Object ? Str(ev, "type") : null;
            var id = Str(payload, "event_id");
            return type is null || id is null ? new(400) : new(200, type, id);
        }
        return kind is null ? new(400) : new(200, kind, null);
    }

    static string? Str(JsonElement obj, string name) =>
        obj.TryGetProperty(name, out var v) && v.ValueKind == JsonValueKind.String ? v.GetString() : null;
}

/// <summary>application/x-www-form-urlencoded parsing ("+" is a space, then percent-decoding).</summary>
public static class Form
{
    public static List<KeyValuePair<string, string>> Parse(string body) =>
        body.Split('&', StringSplitOptions.RemoveEmptyEntries)
            .Select(pair => pair.Split('=', 2))
            .Select(kv => new KeyValuePair<string, string>(Decode(kv[0]), kv.Length > 1 ? Decode(kv[1]) : ""))
            .ToList();

    static string Decode(string s) => Uri.UnescapeDataString(s.Replace('+', ' '));
}
