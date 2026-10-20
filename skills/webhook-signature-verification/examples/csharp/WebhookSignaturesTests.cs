// Checks WebhookSignatures.cs against ../fixtures/vectors.json (signed by the openssl command line,
// make_vectors.py) and ../fixtures/published.json (the providers' own published examples), and
// against the failure cases every verifier must reject.

using System.Text;
using System.Text.Json;
using Xunit;

namespace WebhookSignatures;

public class VerifyTests
{
    private static List<JsonElement> Load(string file)
        => JsonSerializer.Deserialize<List<JsonElement>>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "fixtures", file)))!;

    public static TheoryData<string> Vectors()
    {
        var data = new TheoryData<string>();
        foreach (var v in Load("vectors.json").Concat(Load("published.json"))) data.Add(v.GetRawText());
        return data;
    }

    private static string? S(JsonElement v, string name) => v.TryGetProperty(name, out var p) && p.ValueKind == JsonValueKind.String ? p.GetString() : null;
    private static long Now(JsonElement v) => v.GetProperty("now").GetInt64();
    private static long Tol(JsonElement v) => v.TryGetProperty("tolerance", out var t) ? t.GetInt64() : 300;
    private static byte[] Body(JsonElement v) => Encoding.UTF8.GetBytes(S(v, "body") ?? "");

    /// <summary>Verifies one vector with optional overrides: body, signature (or header), secret, now, url.</summary>
    private static bool Call(JsonElement v, byte[]? body = null, string? signature = null, string? secret = null, long? now = null, string? url = null, bool missing = false)
    {
        body ??= Body(v);
        var sig = missing ? null : signature ?? S(v, "signature");
        var key = secret ?? S(v, "secret");
        var at = now ?? (v.TryGetProperty("now", out _) ? Now(v) : 0);
        return S(v, "family") switch
        {
            "hmac-body" => Verify.HmacBody(body, sig, key, S(v, "encoding")!, S(v, "prefix")!),
            "hmac-timestamp-header" => Verify.TimestampHeader(body, missing ? null : signature ?? S(v, "header"), key, at, Tol(v),
                S(v, "pairSeparator")![0], S(v, "timestampKey")!, S(v, "signatureKey")!, S(v, "joiner")!),
            "hmac-versioned-timestamp" => Verify.VersionedTimestamp(body, S(v, "timestamp"), sig, key, at, Tol(v)),
            "standard-webhooks" => Verify.StandardWebhooks(body, S(v, "id"), S(v, "timestamp"), sig, key, at, Tol(v)),
            "hmac-url-form" => Verify.UrlForm(url ?? S(v, "url"),
                v.GetProperty("params").EnumerateObject().ToDictionary(p => p.Name, p => p.Value.GetString()!), sig, key),
            "ed25519" => Verify.Ed25519(body, S(v, "timestamp"), sig, S(v, "publicKey"), at, Tol(v)),
            "ecdsa-p256" => Verify.EcdsaP256(body, S(v, "timestamp"), sig, S(v, "publicKey"), at, Tol(v)),
            "shared-token" => Verify.SharedToken(sig, key),
            var other => throw new InvalidOperationException($"no test mapping for family {other}"),
        };
    }

    private static readonly Dictionary<string, string> WrongSecret = new()
    {
        ["hmac-body"] = "test-wrong-secret",
        ["hmac-timestamp-header"] = "test-wrong-secret",
        ["hmac-versioned-timestamp"] = "test-wrong-secret",
        ["standard-webhooks"] = "whsec_" + Convert.ToBase64String(Enumerable.Repeat((byte)7, 32).ToArray()),
        ["hmac-url-form"] = "test-wrong-token",
        ["shared-token"] = "test-other-token",
    };

    private static readonly HashSet<string> Timed = ["hmac-timestamp-header", "hmac-versioned-timestamp", "standard-webhooks", "ed25519", "ecdsa-p256"];

    [Theory, MemberData(nameof(Vectors))]
    public void the_signature_verifies_and_every_mutation_is_rejected(string json)
    {
        var v = JsonDocument.Parse(json).RootElement;
        var family = S(v, "family")!;

        Assert.True(Call(v));
        Assert.False(Call(v, missing: true));
        Assert.False(Call(v, signature: "%%%not-a-signature%%%"));
        Assert.False(Call(v, signature: "nonsense;;==,,"));
        if (S(v, "body") is { } text)
        {
            Assert.False(Call(v, body: [.. Body(v), (byte)' ']));
            if (text.StartsWith('{'))
            {
                var reserialised = JsonSerializer.Serialize(JsonDocument.Parse(text).RootElement, new JsonSerializerOptions { WriteIndented = true });
                if (reserialised != text) Assert.False(Call(v, body: Encoding.UTF8.GetBytes(reserialised)));
            }
        }
        if (WrongSecret.TryGetValue(family, out var wrong)) Assert.False(Call(v, secret: wrong));
        if (Timed.Contains(family)) Assert.False(Call(v, now: Now(v) + 10_000));
    }

    [Fact]
    public void a_url_rebuilt_behind_a_proxy_fails()
    {
        var v = Load("vectors.json").First(x => S(x, "family") == "hmac-url-form");
        Assert.False(Call(v, url: S(v, "url")!.Replace("https://", "http://")));
    }

    [Fact]
    public void a_header_with_two_timestamps_is_rejected()
    {
        var v = Load("vectors.json").First(x => S(x, "family") == "hmac-timestamp-header" && S(x, "name") == "comma-json");
        Assert.False(Call(v, signature: "t=1," + S(v, "header")));
    }

    [Fact]
    public void freshness_accepts_whole_seconds_within_the_tolerance_only()
    {
        Assert.True(Verify.IsFresh("1000", 1200, 300));
        Assert.False(Verify.IsFresh("1000", 1301, 300));
        Assert.False(Verify.IsFresh("1000", 699, 300));
        Assert.False(Verify.IsFresh("1000.5", 1000, 300));
        Assert.False(Verify.IsFresh("", 1000, 300));
        Assert.False(Verify.IsFresh(null, 1000, 300));
    }

    [Fact]
    public void safe_equal_is_false_for_different_lengths_and_null()
    {
        Assert.False(Verify.SafeEqual("abc", "abcd"));
        Assert.False(Verify.SafeEqual(null, "a"));
        Assert.True(Verify.SafeEqual("a", "a"));
    }
}
