// Verifies and reads Lemon Squeezy webhooks. Framework-free: pass the raw body bytes and the
// headers; wire it into ASP.NET Core as shown in the webhook-receiver-patterns skill.
// .NET 9 or later, no packages.
//
// Lemon Squeezy signs the raw body with HMAC-SHA256 and the webhook's signing secret, hex encoded,
// in X-Signature. There is no timestamp and no event or delivery id. The event name is read from
// the signed body (meta.event_name); the unsigned X-Event-Name header is only cross-checked.

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace LemonSqueezyWebhooksExample;

/// <summary>What to answer, and what was received. Type and Resource are set when Status is 200; Id is always null.</summary>
public sealed record LemonSqueezyResult(int Status, string? Type = null, string? Id = null, string? Resource = null);

public static class LemonSqueezyWebhooks
{
    static string? Header(IEnumerable<KeyValuePair<string, string>> headers, string name) =>
        headers.FirstOrDefault(h => string.Equals(h.Key, name, StringComparison.OrdinalIgnoreCase)).Value;

    /// <summary>True when the request carries a valid Lemon Squeezy signature over these exact bytes.</summary>
    public static bool Verify(byte[] body, IEnumerable<KeyValuePair<string, string>> headers, string secret)
    {
        if (string.IsNullOrEmpty(secret)) throw new ArgumentException("The Lemon Squeezy signing secret is required (read it from configuration).", nameof(secret));
        var sig = Header(headers, "X-Signature");
        if (sig is null) return false;
        var expected = Convert.ToHexStringLower(HMACSHA256.HashData(Encoding.UTF8.GetBytes(secret), body));
        return CryptographicOperations.FixedTimeEquals(Encoding.UTF8.GetBytes(sig), Encoding.UTF8.GetBytes(expected));
    }

    /// <summary>
    /// Handles one request: verify, then parse. Type is the event name. Id is always null: Lemon
    /// Squeezy sends no id to deduplicate on, so key on Resource plus the event name and a hash of
    /// the body. Resource is "&lt;data.type&gt;/&lt;data.id&gt;" (null when either is missing).
    /// </summary>
    public static LemonSqueezyResult Handle(byte[] body, IEnumerable<KeyValuePair<string, string>> headers, string secret)
    {
        if (!Verify(body, headers, secret)) return new(401);

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

        var type = payload.TryGetProperty("meta", out var meta) && meta.ValueKind == JsonValueKind.Object ? Str(meta, "event_name") : null;
        if (string.IsNullOrEmpty(type)) return new(400);
        var claimed = Header(headers, "X-Event-Name");
        if (claimed is not null && claimed != type) return new(400);

        string? resource = null;
        if (payload.TryGetProperty("data", out var data) && data.ValueKind == JsonValueKind.Object)
        {
            var kind = Str(data, "type");
            var id = Str(data, "id");
            if (!string.IsNullOrEmpty(kind) && !string.IsNullOrEmpty(id)) resource = $"{kind}/{id}";
        }
        return new(200, type, null, resource);
    }

    static string? Str(JsonElement obj, string name) =>
        obj.TryGetProperty(name, out var v) && v.ValueKind == JsonValueKind.String ? v.GetString() : null;
}
