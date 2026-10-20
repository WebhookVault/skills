// Webhook signature verification for the common scheme families. .NET 9 or later.
//
// The HMAC families and ECDSA use System.Security.Cryptography. Ed25519 is not in the base library,
// so it uses BouncyCastle.Cryptography. Every method takes the RAW body bytes exactly as received
// (read the request body as bytes before any JSON parsing) and returns true or false without
// throwing. `now` is the current Unix time in seconds, a parameter so tests are deterministic.

using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using Org.BouncyCastle.Crypto.Parameters;
using Org.BouncyCastle.Crypto.Signers;

namespace WebhookSignatures;

public static partial class Verify
{
    public static long Now() => DateTimeOffset.UtcNow.ToUnixTimeSeconds();

    /// <summary>Constant-time comparison of two strings; false when either is null.</summary>
    public static bool SafeEqual(string? a, string? b)
    {
        if (a is null || b is null) return false;
        return CryptographicOperations.FixedTimeEquals(Encoding.UTF8.GetBytes(a), Encoding.UTF8.GetBytes(b));
    }

    [GeneratedRegex(@"^\d{1,12}$")] private static partial Regex Seconds();
    [GeneratedRegex(@"^[0-9a-fA-F]{64}$")] private static partial Regex Hex64();
    [GeneratedRegex(@"^[0-9a-fA-F]{128}$")] private static partial Regex Hex128();

    /// <summary>True when the timestamp is whole Unix seconds within the tolerance of now.</summary>
    public static bool IsFresh(string? timestamp, long now, long tolerance = 300)
        => timestamp is not null && Seconds().IsMatch(timestamp) && Math.Abs(now - long.Parse(timestamp)) <= tolerance;

    private static byte[] Concat(string prefix, byte[] body) => [.. Encoding.UTF8.GetBytes(prefix), .. body];

    /// <summary>HMAC-SHA256 over the raw body; encoding "hex" or "base64"; prefix such as "sha256=".</summary>
    public static bool HmacBody(byte[] body, string? signature, string? secret, string encoding = "hex", string prefix = "")
    {
        if (string.IsNullOrEmpty(secret) || signature is null) return false;
        var mac = HMACSHA256.HashData(Encoding.UTF8.GetBytes(secret), body);
        var expected = prefix + (encoding == "hex" ? Convert.ToHexStringLower(mac) : Convert.ToBase64String(mac));
        return SafeEqual(signature, expected);
    }

    /// <summary>
    /// A timestamp and one or more signatures in one header ("t=1,v1=abc" over "&lt;t&gt;.&lt;body&gt;", or
    /// "ts=1;h1=abc" over "&lt;ts&gt;:&lt;body&gt;"). Any one signature entry matching is enough (rotation).
    /// </summary>
    public static bool TimestampHeader(byte[] body, string? header, string? secret, long now, long tolerance = 300,
        char pairSeparator = ',', string timestampKey = "t", string signatureKey = "v1", string joiner = ".")
    {
        if (string.IsNullOrEmpty(secret) || header is null) return false;
        var pairs = header.Split(pairSeparator).Select(p =>
        {
            var i = p.IndexOf('=');
            return i < 0 ? (Key: p.Trim(), Value: "") : (Key: p[..i].Trim(), Value: p[(i + 1)..].Trim());
        }).ToList();
        var stamps = pairs.Where(p => p.Key == timestampKey).Select(p => p.Value).ToList();
        if (stamps.Count != 1 || !IsFresh(stamps[0], now, tolerance)) return false;
        var expected = Convert.ToHexStringLower(HMACSHA256.HashData(Encoding.UTF8.GetBytes(secret), Concat(stamps[0] + joiner, body)));
        return pairs.Any(p => p.Key == signatureKey && SafeEqual(p.Value, expected));
    }

    /// <summary>A timestamp in its own header and "v0=&lt;hex&gt;" over "v0:&lt;timestamp&gt;:&lt;body&gt;".</summary>
    public static bool VersionedTimestamp(byte[] body, string? timestamp, string? signature, string? secret, long now, long tolerance = 300, string version = "v0")
    {
        if (string.IsNullOrEmpty(secret) || !IsFresh(timestamp, now, tolerance)) return false;
        var mac = HMACSHA256.HashData(Encoding.UTF8.GetBytes(secret), Concat($"{version}:{timestamp}:", body));
        return SafeEqual(signature, $"{version}=" + Convert.ToHexStringLower(mac));
    }

    /// <summary>Standard Webhooks: "whsec_" plus base64 key; "&lt;id&gt;.&lt;timestamp&gt;.&lt;body&gt;"; "v1,&lt;base64&gt;" entries.</summary>
    public static bool StandardWebhooks(byte[] body, string? id, string? timestamp, string? signature, string? secret, long now, long tolerance = 300)
    {
        if (secret is null || !secret.StartsWith("whsec_", StringComparison.Ordinal) || string.IsNullOrEmpty(id) || signature is null) return false;
        if (!IsFresh(timestamp, now, tolerance)) return false;
        byte[] key;
        try { key = Convert.FromBase64String(secret["whsec_".Length..]); }
        catch (FormatException) { return false; }
        if (key.Length == 0) return false;
        var expected = Convert.ToBase64String(HMACSHA256.HashData(key, Concat($"{id}.{timestamp}.", body)));
        foreach (var entry in signature.Split(' '))
        {
            var comma = entry.IndexOf(',');
            if (comma > 0 && entry[..comma] == "v1" && SafeEqual(entry[(comma + 1)..], expected)) return true;
        }
        return false;
    }

    /// <summary>
    /// HMAC-SHA1 over the full URL the sender called plus form fields sorted by name (ordinal), base64.
    /// The URL comes from your configuration, never from the incoming request.
    /// </summary>
    public static bool UrlForm(string? url, IReadOnlyDictionary<string, string>? parameters, string? signature, string? secret)
    {
        if (string.IsNullOrEmpty(secret) || url is null || signature is null) return false;
        var data = new StringBuilder(url);
        foreach (var name in (parameters ?? new Dictionary<string, string>()).Keys.Order(StringComparer.Ordinal))
            data.Append(name).Append(parameters![name]);
        var expected = Convert.ToBase64String(HMACSHA1.HashData(Encoding.UTF8.GetBytes(secret), Encoding.UTF8.GetBytes(data.ToString())));
        return SafeEqual(signature, expected);
    }

    /// <summary>Ed25519 over "&lt;timestamp&gt;&lt;body&gt;"; hex signature; the public key as 64 hex characters.</summary>
    public static bool Ed25519(byte[] body, string? timestamp, string? signature, string? publicKey, long now, long tolerance = 300)
    {
        if (publicKey is null || !Hex64().IsMatch(publicKey) || signature is null || !Hex128().IsMatch(signature)) return false;
        if (!IsFresh(timestamp, now, tolerance)) return false;
        try
        {
            var verifier = new Ed25519Signer();
            verifier.Init(false, new Ed25519PublicKeyParameters(Convert.FromHexString(publicKey), 0));
            var message = Concat(timestamp!, body);
            verifier.BlockUpdate(message, 0, message.Length);
            return verifier.VerifySignature(Convert.FromHexString(signature));
        }
        catch (ArgumentException) { return false; }
    }

    /// <summary>ECDSA P-256 with SHA-256 over "&lt;timestamp&gt;&lt;body&gt;"; base64 DER signature; base64 SPKI public key.</summary>
    public static bool EcdsaP256(byte[] body, string? timestamp, string? signature, string? publicKey, long now, long tolerance = 300)
    {
        if (publicKey is null || signature is null || !IsFresh(timestamp, now, tolerance)) return false;
        try
        {
            using var key = ECDsa.Create();
            key.ImportSubjectPublicKeyInfo(Convert.FromBase64String(publicKey), out _);
            if (key.KeySize != 256) return false;
            return key.VerifyData(Concat(timestamp!, body), Convert.FromBase64String(signature), HashAlgorithmName.SHA256, DSASignatureFormat.Rfc3279DerSequence);
        }
        catch (Exception e) when (e is FormatException or CryptographicException) { return false; }
    }

    /// <summary>A shared token sent in a header (no signature), compared in constant time.</summary>
    public static bool SharedToken(string? value, string? token) => !string.IsNullOrEmpty(token) && SafeEqual(value, token);
}
