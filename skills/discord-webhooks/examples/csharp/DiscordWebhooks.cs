// Verifies and reads Discord Webhook Events and Interactions endpoint requests. Framework-free: pass the
// raw body bytes and the headers; wire it into ASP.NET Core as shown in the webhook-receiver-patterns
// skill. .NET 9 or later; needs BouncyCastle.Cryptography for Ed25519, which .NET does not include.
//
// Both use the same signature: Ed25519 over "<X-Signature-Timestamp><raw body>", hex encoded in
// X-Signature-Ed25519, checked with the application's public key (64 hex characters, from the
// developer portal). Discord sends no tolerance guidance for it and neither does this code: the
// timestamp is part of the signed message, nothing more. Discord also sends requests with a bad
// signature on purpose when you save the endpoint URL and expects 401 for them.
//
// HandleEvent is for Webhook Events (answer 204); HandleInteraction is for the Interactions endpoint
// (answer 200 with a JSON body). Use the one that matches the URL you registered.

using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Org.BouncyCastle.Crypto.Parameters;
using Org.BouncyCastle.Crypto.Signers;

namespace DiscordWebhooksExample;

/// <summary>
/// What to answer, and what was received. For events Type is the event name or "PING"; for
/// interactions Type is the integer type as text, Id the interaction id and Reply the body to send
/// for a PING (null otherwise).
/// </summary>
public sealed record DiscordResult(int Status, string? Type = null, string? Id = null, string? Reply = null);

public static partial class DiscordWebhooks
{
    [GeneratedRegex("^[0-9a-fA-F]{128}$")]
    private static partial Regex HexSignature();

    [GeneratedRegex("^[0-9a-fA-F]{64}$")]
    private static partial Regex HexKey();

    static string? Header(IEnumerable<KeyValuePair<string, string>> headers, string name) =>
        headers.FirstOrDefault(h => string.Equals(h.Key, name, StringComparison.OrdinalIgnoreCase)).Value;

    /// <summary>True when the request carries a valid Discord Ed25519 signature over these exact bytes.</summary>
    public static bool Verify(byte[] body, IEnumerable<KeyValuePair<string, string>> headers, string publicKey)
    {
        if (string.IsNullOrEmpty(publicKey)) throw new ArgumentException("The Discord application public key is required (read it from configuration).", nameof(publicKey));
        var ts = Header(headers, "X-Signature-Timestamp");
        var sig = Header(headers, "X-Signature-Ed25519");
        if (string.IsNullOrEmpty(ts) || sig is null) return false;
        if (!HexSignature().IsMatch(sig) || !HexKey().IsMatch(publicKey)) return false;

        var message = new byte[Encoding.UTF8.GetByteCount(ts) + body.Length];
        var written = Encoding.UTF8.GetBytes(ts, message);
        body.CopyTo(message, written);

        var verifier = new Ed25519Signer();
        verifier.Init(false, new Ed25519PublicKeyParameters(Convert.FromHexString(publicKey), 0));
        verifier.BlockUpdate(message, 0, message.Length);
        return verifier.VerifySignature(Convert.FromHexString(sig));
    }

    static JsonElement? ParseObject(byte[] body)
    {
        try
        {
            var root = JsonDocument.Parse(body).RootElement;
            return root.ValueKind == JsonValueKind.Object ? root : null;
        }
        catch (JsonException)
        {
            return null;
        }
    }

    /// <summary>
    /// Webhook Events: verify, then parse. A PING (outer type 0) answers 204 with type "PING"; an event
    /// (outer type 1) answers 204 with Type = event.type, e.g. APPLICATION_AUTHORIZED. Discord does not
    /// document an event id, so there is nothing to deduplicate on in the envelope.
    /// </summary>
    public static DiscordResult HandleEvent(byte[] body, IEnumerable<KeyValuePair<string, string>> headers, string publicKey)
    {
        if (!Verify(body, headers, publicKey)) return new(401);
        if (ParseObject(body) is not { } payload) return new(400);

        if (!payload.TryGetProperty("type", out var outer) || outer.ValueKind != JsonValueKind.Number || !outer.TryGetInt32(out var kind)) return new(400);
        if (kind == 0) return new(204, "PING");
        if (kind == 1
            && payload.TryGetProperty("event", out var ev) && ev.ValueKind == JsonValueKind.Object
            && ev.TryGetProperty("type", out var t) && t.ValueKind == JsonValueKind.String)
            return new(204, t.GetString());
        return new(400);
    }

    /// <summary>
    /// Interactions endpoint: verify, then parse. Type is the integer interaction type (as text) and Id
    /// the interaction id. For a PING (type 1) Reply is the exact body to answer with, {"type":1}; for
    /// anything else it is null and you answer with a real interaction response within three seconds.
    /// </summary>
    public static DiscordResult HandleInteraction(byte[] body, IEnumerable<KeyValuePair<string, string>> headers, string publicKey)
    {
        if (!Verify(body, headers, publicKey)) return new(401);
        if (ParseObject(body) is not { } payload) return new(400);

        if (!payload.TryGetProperty("type", out var t) || t.ValueKind != JsonValueKind.Number || !t.TryGetInt32(out var kind)) return new(400);
        if (!payload.TryGetProperty("id", out var id) || id.ValueKind != JsonValueKind.String) return new(400);
        return new(200, kind.ToString(), id.GetString(), kind == 1 ? "{\"type\":1}" : null);
    }
}
