// Runs every case in ../fixtures/vectors.json (made with the openssl command line) against
// PayPalWebhooks.cs. fetchCertificate answers from the vectors' certificates and throws for any URL
// not listed there, so a request that reaches the network for a URL the rule should have refused
// fails the test.

using System.Text;
using System.Text.Json;
using PayPalWebhooksExample;
using Xunit;

public class PayPalWebhooksTests
{
    static readonly JsonElement Vectors = JsonDocument.Parse(File.ReadAllText(
        Path.Combine(AppContext.BaseDirectory, "fixtures", "vectors.json"))).RootElement;

    static string FetchCertificate(string url) =>
        Vectors.GetProperty("config").GetProperty("certificates").TryGetProperty(url, out var pem)
            ? pem.GetString()!
            : throw new InvalidOperationException($"no certificate for {url}");

    static string WebhookId => Vectors.GetProperty("config").GetProperty("webhookId").GetString()!;

    public static TheoryData<string> Cases()
    {
        var data = new TheoryData<string>();
        foreach (var c in Vectors.GetProperty("cases").EnumerateArray()) data.Add(c.GetProperty("name").GetString()!);
        return data;
    }

    [Theory]
    [MemberData(nameof(Cases))]
    public void Case(string name)
    {
        var c = Vectors.GetProperty("cases").EnumerateArray().Single(x => x.GetProperty("name").GetString() == name);
        var headers = c.GetProperty("headers").EnumerateObject().Select(p => KeyValuePair.Create(p.Name, p.Value.GetString()!)).ToList();
        var body = Encoding.UTF8.GetBytes(c.GetProperty("body").GetString()!);
        var expect = c.GetProperty("expect");

        if (c.TryGetProperty("verifyOnly", out var vo) && vo.GetBoolean())
        {
            Assert.Equal(expect.GetProperty("verified").GetBoolean(), PayPalWebhooks.Verify(body, headers, WebhookId, FetchCertificate));
            return;
        }

        var got = PayPalWebhooks.Handle(body, headers, WebhookId, FetchCertificate);
        Assert.Equal(expect.GetProperty("status").GetInt32(), got.Status);
        if (expect.TryGetProperty("type", out var type)) Assert.Equal(type.GetString(), got.Type);
        if (expect.TryGetProperty("id", out var id)) Assert.Equal(id.ValueKind == JsonValueKind.Null ? null : id.GetString(), got.Id);
    }

    [Fact]
    public void Refuses_to_run_without_a_webhook_id() =>
        Assert.Throws<ArgumentException>(() => PayPalWebhooks.Verify([], [], "", FetchCertificate));

    [Fact]
    public void Refuses_to_run_without_a_certificate_fetcher() =>
        Assert.Throws<ArgumentNullException>(() => PayPalWebhooks.Handle([], [], "x", null!));

    [Fact]
    public void Crc32_matches_the_standard_check_value()
    {
        Assert.Equal(0xCBF43926u, PayPalWebhooks.Crc32("123456789"u8));
        Assert.Equal(0u, PayPalWebhooks.Crc32([]));
    }

    [Theory]
    [InlineData("https://api.paypal.com/v1/notifications/certs/C", true)]
    [InlineData("https://paypal.com/c", true)]
    [InlineData("https://evilpaypal.com/c", false)]
    [InlineData("https://paypal.com@evil.test/c", false)]
    [InlineData("https://user:pw@api.paypal.com/c", false)]
    [InlineData("https://api.paypal.com:8443/c", false)]
    [InlineData("http://api.paypal.com/c", false)]
    [InlineData("not a url", false)]
    public void Certificate_url_rule(string url, bool trusted) =>
        Assert.Equal(trusted, PayPalWebhooks.IsTrustedCertificateUrl(url));
}
