// Verifies and reads Shopify webhooks. Framework-free: pass the raw body bytes and the headers; wire
// it into ASP.NET Core as shown in the webhook-receiver-patterns skill.
// .NET 8 or later, no packages.
//
// Shopify signs the raw body with HMAC-SHA256 and the app's client secret, base64 encoded (not hex),
// in X-Shopify-Hmac-Sha256. There is no timestamp. X-Shopify-Webhook-Id is the same on every
// delivery attempt of one webhook, X-Shopify-Event-Id is shared by all webhooks for one event:
// deduplicate on the first, or on the second to collapse subscriptions to the same event.

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace ShopifyWebhooksExample;

/// <summary>What to answer, and what was received. The other fields are set when Status is 200.</summary>
public sealed record ShopifyResult(int Status, string? Type = null, string? Id = null, string? EventId = null, string? Shop = null);

public static class ShopifyWebhooks
{
    static string? Header(IEnumerable<KeyValuePair<string, string>> headers, string name) =>
        headers.FirstOrDefault(h => string.Equals(h.Key, name, StringComparison.OrdinalIgnoreCase)).Value;

    /// <summary>True when the request carries a valid Shopify signature over these exact bytes.</summary>
    public static bool Verify(byte[] body, IEnumerable<KeyValuePair<string, string>> headers, string secret)
    {
        if (string.IsNullOrEmpty(secret)) throw new ArgumentException("The Shopify client secret is required (read it from configuration).", nameof(secret));
        var sig = Header(headers, "X-Shopify-Hmac-Sha256");
        if (sig is null) return false;
        var expected = Convert.ToBase64String(HMACSHA256.HashData(Encoding.UTF8.GetBytes(secret), body));
        return CryptographicOperations.FixedTimeEquals(Encoding.UTF8.GetBytes(sig), Encoding.UTF8.GetBytes(expected));
    }

    /// <summary>
    /// Handles one request: verify, then parse. Type is the topic, Id the webhook id to deduplicate
    /// on, EventId the event id and Shop the shop's domain. Answer within five seconds: queue the
    /// work and process it elsewhere.
    /// </summary>
    public static ShopifyResult Handle(byte[] body, IEnumerable<KeyValuePair<string, string>> headers, string secret)
    {
        if (!Verify(body, headers, secret)) return new(401);

        var type = Header(headers, "X-Shopify-Topic");
        var id = Header(headers, "X-Shopify-Webhook-Id");
        if (string.IsNullOrEmpty(type) || string.IsNullOrEmpty(id)) return new(400);
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

        var eventId = Header(headers, "X-Shopify-Event-Id");
        var shop = Header(headers, "X-Shopify-Shop-Domain");
        return new(200, type, id, string.IsNullOrEmpty(eventId) ? null : eventId, string.IsNullOrEmpty(shop) ? null : shop);
    }
}
