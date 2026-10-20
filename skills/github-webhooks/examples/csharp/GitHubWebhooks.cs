// Verifies and reads GitHub webhook deliveries. Framework-free: pass the raw body bytes and the
// headers; wire it into ASP.NET Core as shown in the webhook-receiver-patterns skill.
// .NET 9 or later, no packages.
//
// GitHub signs the raw body with HMAC-SHA256 and the webhook's secret, hex encoded and prefixed
// "sha256=", in X-Hub-Signature-256. The older SHA-1 X-Hub-Signature header is never accepted.
// There is no timestamp, so a replayed delivery verifies: deduplicate on X-GitHub-Delivery.
// Set the webhook's content type to application/json (a form-encoded delivery is not read here).

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace GitHubWebhooksExample;

/// <summary>What to answer, and what was received. Type, Action and Id are set when Status is 200.</summary>
public sealed record GitHubResult(int Status, string? Type = null, string? Action = null, string? Id = null);

public static class GitHubWebhooks
{
    static string? Header(IEnumerable<KeyValuePair<string, string>> headers, string name) =>
        headers.FirstOrDefault(h => string.Equals(h.Key, name, StringComparison.OrdinalIgnoreCase)).Value;

    /// <summary>True when the request carries a valid GitHub SHA-256 signature over these exact bytes.</summary>
    public static bool Verify(byte[] body, IEnumerable<KeyValuePair<string, string>> headers, string secret)
    {
        if (string.IsNullOrEmpty(secret)) throw new ArgumentException("The GitHub webhook secret is required (read it from configuration).", nameof(secret));
        var sig = Header(headers, "X-Hub-Signature-256");
        if (sig is null) return false;
        var expected = "sha256=" + Convert.ToHexStringLower(HMACSHA256.HashData(Encoding.UTF8.GetBytes(secret), body));
        return CryptographicOperations.FixedTimeEquals(Encoding.UTF8.GetBytes(sig), Encoding.UTF8.GetBytes(expected));
    }

    /// <summary>
    /// Handles one request: verify, then parse. Type is X-GitHub-Event, Action the body's action
    /// (null when it has none) and Id the X-GitHub-Delivery to deduplicate on. Answer within ten
    /// seconds: queue the work and process it elsewhere.
    /// </summary>
    public static GitHubResult Handle(byte[] body, IEnumerable<KeyValuePair<string, string>> headers, string secret)
    {
        if (!Verify(body, headers, secret)) return new(401);

        var type = Header(headers, "X-GitHub-Event");
        if (string.IsNullOrEmpty(type)) return new(400);
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

        var delivery = Header(headers, "X-GitHub-Delivery");
        var action = payload.TryGetProperty("action", out var a) && a.ValueKind == JsonValueKind.String ? a.GetString() : null;
        return new(200, type, action, string.IsNullOrEmpty(delivery) ? null : delivery);
    }
}
