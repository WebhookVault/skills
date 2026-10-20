// Verifies and reads PayPal webhooks. Framework-free: pass the raw body bytes and the headers; wire it
// into ASP.NET Core as shown in the webhook-receiver-patterns skill.
// .NET 9 or later, no packages.
//
// PayPal signs "<PAYPAL-TRANSMISSION-ID>|<PAYPAL-TRANSMISSION-TIME>|<webhook id>|<crc32>", where crc32
// is the CRC-32 (IEEE, as zlib) of the raw body as an unsigned decimal number. The signature is RSA
// PKCS#1 v1.5 with SHA-256, base64 encoded, in PAYPAL-TRANSMISSION-SIG, and PAYPAL-AUTH-ALGO must be
// SHA256withRSA. The public key is the certificate at PAYPAL-CERT-URL, so that header is attacker
// controlled until proven otherwise: a certificate fetched from anywhere else would let anyone sign.
// PayPal's docs do not state a host rule, so this one is ours: the URL must be https, on paypal.com or a
// subdomain of it, with no userinfo and no non-default port. Only a URL that passes is ever fetched.
//
// Pass fetchCertificate, which returns the certificate as PEM text for a URL (block on your async
// fetch, or fetch before calling). Cache the certificates by URL: they change rarely, and fetching on
// every webhook adds latency and a failure mode. A fetch that throws gives 500 so PayPal retries; it is
// not a verdict on the signature.

using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace PayPalWebhooksExample;

/// <summary>What to answer, and what was received. Type and Id are set when Status is 200.</summary>
public sealed record PayPalResult(int Status, string? Type = null, string? Id = null);

/// <summary>The certificate could not be fetched (not a verdict on the signature).</summary>
public sealed class CertificateFetchException(string message, Exception inner) : Exception(message, inner);

public static partial class PayPalWebhooks
{
    static readonly uint[] CrcTable = BuildCrcTable();

    static uint[] BuildCrcTable()
    {
        var table = new uint[256];
        for (uint n = 0; n < 256; n++)
        {
            var c = n;
            for (var k = 0; k < 8; k++) c = (c & 1) != 0 ? 0xEDB88320u ^ (c >> 1) : c >> 1;
            table[n] = c;
        }
        return table;
    }

    /// <summary>CRC-32 (IEEE 802.3, the same value as zlib.crc32) of the bytes, as an unsigned integer.</summary>
    public static uint Crc32(ReadOnlySpan<byte> bytes)
    {
        var c = 0xFFFFFFFFu;
        foreach (var b in bytes) c = CrcTable[(c ^ b) & 0xFF] ^ (c >> 8);
        return c ^ 0xFFFFFFFFu;
    }

    static string? Header(IEnumerable<KeyValuePair<string, string>> headers, string name) =>
        headers.FirstOrDefault(h => string.Equals(h.Key, name, StringComparison.OrdinalIgnoreCase)).Value;

    [GeneratedRegex("^[a-z0-9.-]+$")]
    private static partial Regex HostCharacters();

    /// <summary>True only for an https URL on paypal.com or a subdomain, with no userinfo and the default port.</summary>
    public static bool IsTrustedCertificateUrl(string value)
    {
        if (!Uri.TryCreate(value, UriKind.Absolute, out var url)) return false;
        if (url.Scheme != Uri.UriSchemeHttps || url.UserInfo.Length != 0 || !url.IsDefaultPort) return false;
        var host = url.Host;
        if (!HostCharacters().IsMatch(host)) return false;
        return host == "paypal.com" || host.EndsWith(".paypal.com", StringComparison.Ordinal);
    }

    static void Require(string webhookId, Func<string, string> fetchCertificate)
    {
        if (string.IsNullOrEmpty(webhookId)) throw new ArgumentException("The PayPal webhook id is required (read it from configuration).", nameof(webhookId));
        ArgumentNullException.ThrowIfNull(fetchCertificate);
    }

    /// <summary>
    /// True when the request carries a valid PayPal signature over these exact bytes. Throws
    /// CertificateFetchException when the certificate could not be fetched.
    /// </summary>
    public static bool Verify(byte[] body, IEnumerable<KeyValuePair<string, string>> headers, string webhookId, Func<string, string> fetchCertificate)
    {
        Require(webhookId, fetchCertificate);
        var id = Header(headers, "PAYPAL-TRANSMISSION-ID");
        var time = Header(headers, "PAYPAL-TRANSMISSION-TIME");
        var sig = Header(headers, "PAYPAL-TRANSMISSION-SIG");
        var certUrl = Header(headers, "PAYPAL-CERT-URL");
        var algo = Header(headers, "PAYPAL-AUTH-ALGO");
        if (string.IsNullOrEmpty(id) || string.IsNullOrEmpty(time) || string.IsNullOrEmpty(sig) || string.IsNullOrEmpty(certUrl)) return false;
        if (algo != "SHA256withRSA") return false;
        if (!IsTrustedCertificateUrl(certUrl)) return false;

        string pem;
        try
        {
            pem = fetchCertificate(certUrl);
        }
        catch (Exception ex)
        {
            throw new CertificateFetchException($"Could not fetch the PayPal certificate: {ex.Message}", ex);
        }

        try
        {
            using var certificate = X509Certificate2.CreateFromPem(pem);
            using var rsa = certificate.GetRSAPublicKey();
            if (rsa is null) return false;
            var signed = Encoding.UTF8.GetBytes($"{id}|{time}|{webhookId}|{Crc32(body)}");
            return rsa.VerifyData(signed, Convert.FromBase64String(sig), HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
        }
        catch (Exception ex) when (ex is CryptographicException or FormatException or ArgumentException)
        {
            return false; // bad signature encoding, not a certificate, or not usable for RSA
        }
    }

    /// <summary>
    /// Handles one request: verify, then parse. Type is event_type and Id the body's id (the id to
    /// deduplicate on). 500 means the certificate could not be fetched: PayPal will retry.
    /// </summary>
    public static PayPalResult Handle(byte[] body, IEnumerable<KeyValuePair<string, string>> headers, string webhookId, Func<string, string> fetchCertificate)
    {
        Require(webhookId, fetchCertificate);
        bool valid;
        try
        {
            valid = Verify(body, headers, webhookId, fetchCertificate);
        }
        catch (CertificateFetchException)
        {
            return new(500);
        }
        if (!valid) return new(401);

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
        var type = Str(payload, "event_type");
        var eventId = Str(payload, "id");
        return type is null || eventId is null ? new(400) : new(200, type, eventId);
    }

    static string? Str(JsonElement obj, string name) =>
        obj.TryGetProperty(name, out var v) && v.ValueKind == JsonValueKind.String ? v.GetString() : null;
}
