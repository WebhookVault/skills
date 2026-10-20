// Verifies and reads SendGrid Event Webhook requests (signed event webhook). Framework-free: pass the
// raw body and the headers; wire it into ASP.NET Core as shown in the webhook-receiver-patterns skill.
// .NET 8 or later, no packages.
//
// SendGrid signs the timestamp header value followed by the raw body with ECDSA and SHA-256, and
// sends the base64 signature (DER) in X-Twilio-Email-Event-Webhook-Signature. The verification key is
// the base64 public key shown in the Event Webhook settings. The body is a JSON array of events.

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace SendGridWebhooksExample;

public sealed record SendGridEvent(string? Type, string? Id);

/// <summary>What to answer, and, when Status is 200, each event's name and sg_event_id.</summary>
public sealed record SendGridResult(int Status, IReadOnlyList<SendGridEvent>? Events = null);

public static class SendGridWebhooks
{
    static string? Header(IEnumerable<KeyValuePair<string, string>> headers, string name) =>
        headers.FirstOrDefault(h => string.Equals(h.Key, name, StringComparison.OrdinalIgnoreCase)).Value;

    /// <summary>Loads the base64 key from the SendGrid settings (DER SubjectPublicKeyInfo). Do this once.</summary>
    public static ECDsa LoadPublicKey(string base64Key)
    {
        if (string.IsNullOrEmpty(base64Key)) throw new ArgumentException("The SendGrid verification key is required (read it from configuration).", nameof(base64Key));
        var key = ECDsa.Create();
        key.ImportSubjectPublicKeyInfo(Convert.FromBase64String(base64Key), out _);
        return key;
    }

    /// <summary>True when the signature over timestamp + raw body verifies with this key.</summary>
    public static bool Verify(byte[] body, IEnumerable<KeyValuePair<string, string>> headers, ECDsa publicKey)
    {
        var signature = Header(headers, "X-Twilio-Email-Event-Webhook-Signature");
        var timestamp = Header(headers, "X-Twilio-Email-Event-Webhook-Timestamp");
        if (signature is null || timestamp is null) return false;
        var der = new byte[signature.Length];
        if (!Convert.TryFromBase64String(signature, der, out var length)) return false;

        var stamp = Encoding.UTF8.GetBytes(timestamp);
        var signed = new byte[stamp.Length + body.Length];
        stamp.CopyTo(signed, 0);
        body.CopyTo(signed, stamp.Length);
        try
        {
            return publicKey.VerifyData(signed, der.AsSpan(0, length), HashAlgorithmName.SHA256, DSASignatureFormat.Rfc3279DerSequence);
        }
        catch (CryptographicException)
        {
            return false; // a signature that is not a valid DER sequence
        }
    }

    /// <summary>
    /// Handles one request: verify, then parse the batch. No timestamp window is applied: SendGrid
    /// states none and retries a failed batch for up to 24 hours, so an age limit could refuse its own
    /// retries. Deduplicate on each event's sg_event_id.
    /// </summary>
    public static SendGridResult Handle(byte[] body, IEnumerable<KeyValuePair<string, string>> headers, ECDsa publicKey)
    {
        if (!Verify(body, headers, publicKey)) return new(401);
        try
        {
            using var doc = JsonDocument.Parse(body);
            if (doc.RootElement.ValueKind != JsonValueKind.Array) return new(400);
            var events = new List<SendGridEvent>();
            foreach (var e in doc.RootElement.EnumerateArray())
            {
                if (e.ValueKind != JsonValueKind.Object) return new(400);
                events.Add(new(Str(e, "event"), Str(e, "sg_event_id")));
            }
            return new(200, events);
        }
        catch (JsonException)
        {
            return new(400);
        }
    }

    static string? Str(JsonElement obj, string name) =>
        obj.TryGetProperty(name, out var v) && v.ValueKind == JsonValueKind.String ? v.GetString() : null;
}
