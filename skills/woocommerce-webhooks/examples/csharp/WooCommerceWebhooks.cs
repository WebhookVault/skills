// Verifies and reads WooCommerce webhooks. Framework-free: pass the raw body bytes and the headers;
// wire it into ASP.NET Core as shown in the webhook-receiver-patterns skill.
// .NET 8 or later, no packages.
//
// WooCommerce signs the raw body with HMAC-SHA256 and the webhook's secret, base64 encoded, in
// X-WC-Webhook-Signature. There is no timestamp. When a webhook is saved WooCommerce sends one
// unsigned ping whose body is exactly "webhook_id=<number>"; that single shape is acknowledged and
// nothing else unsigned is.

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace WooCommerceWebhooksExample;

/// <summary>What to answer, and what was received. Type and Id are set when Status is 200.</summary>
public sealed record WooCommerceResult(int Status, string? Type = null, string? Id = null);

public static partial class WooCommerceWebhooks
{
    // \z, not $, because $ would also accept a trailing newline.
    [GeneratedRegex(@"^webhook_id=[0-9]+\z")]
    private static partial Regex PingBody();

    static string? Header(IEnumerable<KeyValuePair<string, string>> headers, string name) =>
        headers.FirstOrDefault(h => string.Equals(h.Key, name, StringComparison.OrdinalIgnoreCase)).Value;

    /// <summary>True when the request carries a valid WooCommerce signature over these exact bytes.</summary>
    public static bool Verify(byte[] body, IEnumerable<KeyValuePair<string, string>> headers, string secret)
    {
        if (string.IsNullOrEmpty(secret)) throw new ArgumentException("The WooCommerce webhook secret is required (read it from configuration).", nameof(secret));
        var sig = Header(headers, "X-WC-Webhook-Signature");
        if (sig is null) return false;
        var expected = Convert.ToBase64String(HMACSHA256.HashData(Encoding.UTF8.GetBytes(secret), body));
        return CryptographicOperations.FixedTimeEquals(Encoding.UTF8.GetBytes(sig), Encoding.UTF8.GetBytes(expected));
    }

    /// <summary>
    /// Handles one request: verify, then parse. Type is the topic (for example "order.created") and
    /// Id the delivery id to deduplicate on (null when WooCommerce sent none). The activation ping
    /// answers 200 with Type "ping" and Id null. Answer quickly: queue the work and process it elsewhere.
    /// </summary>
    public static WooCommerceResult Handle(byte[] body, IEnumerable<KeyValuePair<string, string>> headers, string secret)
    {
        // Only a request with no signature header at all AND exactly this body is the ping.
        if (Header(headers, "X-WC-Webhook-Signature") is null && PingBody().IsMatch(Encoding.Latin1.GetString(body)))
        {
            if (string.IsNullOrEmpty(secret)) throw new ArgumentException("The WooCommerce webhook secret is required (read it from configuration).", nameof(secret));
            return new(200, "ping", null);
        }
        if (!Verify(body, headers, secret)) return new(401);

        var type = Header(headers, "X-WC-Webhook-Topic");
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

        var delivery = Header(headers, "X-WC-Webhook-Delivery-ID");
        return new(200, type, string.IsNullOrEmpty(delivery) ? null : delivery);
    }
}
