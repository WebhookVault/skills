// Verifies and reads Twilio webhook requests (form-encoded and JSON). Framework-free: pass the raw
// body, the headers and the public URL Twilio called; wire it into ASP.NET Core as shown in the
// webhook-receiver-patterns skill. .NET 9 or later, no packages.
//
// Twilio signs with HMAC-SHA1 and the account auth token, base64 encoded, in X-Twilio-Signature.
// Form bodies: the full URL followed by every POST parameter name and value, sorted by name.
// JSON bodies: the URL carries bodySHA256 (hex SHA-256 of the raw body) and nothing is appended.
// The URL must be the one Twilio called, exactly: scheme, host, port, path, query and encoding.

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace TwilioWebhooksExample;

/// <summary>What to answer, and what was received. Type is the reported status, Id the resource SID.</summary>
public sealed record TwilioResult(int Status, string? Type = null, string? Id = null, string? IdempotencyToken = null);

public static class TwilioWebhooks
{
    static string? Header(IEnumerable<KeyValuePair<string, string>> headers, string name) =>
        headers.FirstOrDefault(h => string.Equals(h.Key, name, StringComparison.OrdinalIgnoreCase)).Value;

    static bool IsJson(IEnumerable<KeyValuePair<string, string>> headers) =>
        (Header(headers, "Content-Type") ?? "").StartsWith("application/json", StringComparison.OrdinalIgnoreCase);

    /// <summary>True when X-Twilio-Signature matches this URL and body.</summary>
    public static bool Verify(byte[] body, IEnumerable<KeyValuePair<string, string>> headers, string url, string authToken)
    {
        if (string.IsNullOrEmpty(authToken)) throw new ArgumentException("The Twilio auth token is required (read it from configuration).", nameof(authToken));
        var signature = Header(headers, "X-Twilio-Signature");
        if (signature is null || !Uri.TryCreate(url, UriKind.Absolute, out var uri)) return false;

        var signed = new StringBuilder(url);
        if (IsJson(headers))
        {
            var claimed = Form.Parse(uri.Query.TrimStart('?')).FirstOrDefault(p => p.Key == "bodySHA256").Value;
            if (string.IsNullOrEmpty(claimed)) return false;
            var actual = Convert.ToHexStringLower(SHA256.HashData(body));
            if (!CryptographicOperations.FixedTimeEquals(Encoding.UTF8.GetBytes(claimed.ToLowerInvariant()), Encoding.UTF8.GetBytes(actual))) return false;
        }
        else
        {
            // Sorted by name in ordinal order (Twilio: "Unix-style case-sensitive"); OrderBy is stable,
            // so repeated names keep the order they arrived in.
            foreach (var (name, value) in Form.Parse(Encoding.UTF8.GetString(body)).OrderBy(p => p.Key, StringComparer.Ordinal))
                signed.Append(name).Append(value);
        }
        var expected = Convert.ToBase64String(HMACSHA1.HashData(Encoding.UTF8.GetBytes(authToken), Encoding.UTF8.GetBytes(signed.ToString())));
        return CryptographicOperations.FixedTimeEquals(Encoding.UTF8.GetBytes(signature), Encoding.UTF8.GetBytes(expected));
    }

    /// <summary>
    /// Handles one request: verify, then read. Twilio has no event id; a retry carries
    /// I-Twilio-Idempotency-Token, which is the better key when present.
    /// </summary>
    public static TwilioResult Handle(byte[] body, IEnumerable<KeyValuePair<string, string>> headers, string url, string authToken)
    {
        if (!Verify(body, headers, url, authToken)) return new(401);

        Dictionary<string, string?> fields;
        if (IsJson(headers))
        {
            try
            {
                using var doc = JsonDocument.Parse(body);
                if (doc.RootElement.ValueKind != JsonValueKind.Object) return new(400);
                fields = doc.RootElement.EnumerateObject()
                    .GroupBy(p => p.Name).ToDictionary(g => g.Key, g => g.First().Value.ValueKind == JsonValueKind.String ? g.First().Value.GetString() : null);
            }
            catch (JsonException)
            {
                return new(400);
            }
        }
        else
        {
            fields = Form.Parse(Encoding.UTF8.GetString(body)).GroupBy(p => p.Key).ToDictionary(g => g.Key, g => (string?)g.First().Value);
        }

        string? Pick(params string[] names) => names.Select(n => fields.GetValueOrDefault(n)).FirstOrDefault(v => !string.IsNullOrEmpty(v));
        return new(200, Pick("MessageStatus", "SmsStatus", "CallStatus"), Pick("MessageSid", "SmsSid", "CallSid"), Header(headers, "I-Twilio-Idempotency-Token"));
    }
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
