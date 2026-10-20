// Runs every case in ../fixtures/vectors.json (made with the openssl command line, plus Twilio's own
// published example) against TwilioWebhooks.cs.

using System.Text;
using System.Text.Json;
using TwilioWebhooksExample;
using Xunit;

public class TwilioWebhooksTests
{
    static readonly JsonElement Vectors = JsonDocument.Parse(File.ReadAllText(
        Path.Combine(AppContext.BaseDirectory, "fixtures", "vectors.json"))).RootElement;

    static string Secret => Vectors.GetProperty("config").GetProperty("secret").GetString()!;

    static JsonElement Find(string name) =>
        Vectors.GetProperty("cases").EnumerateArray().Single(x => x.GetProperty("name").GetString() == name);

    static List<KeyValuePair<string, string>> Headers(JsonElement c) =>
        c.GetProperty("headers").EnumerateObject().Select(p => KeyValuePair.Create(p.Name, p.Value.GetString()!)).ToList();

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
        var c = Find(name);
        var body = Encoding.UTF8.GetBytes(c.GetProperty("body").GetString()!);
        var url = c.GetProperty("url").GetString()!;
        var expect = c.GetProperty("expect");

        if (c.TryGetProperty("verifyOnly", out var vo) && vo.GetBoolean())
        {
            Assert.Equal(expect.GetProperty("verified").GetBoolean(), TwilioWebhooks.Verify(body, Headers(c), url, c.GetProperty("secret").GetString()!));
            return;
        }

        var got = TwilioWebhooks.Handle(body, Headers(c), url, Secret);
        Assert.Equal(expect.GetProperty("status").GetInt32(), got.Status);
        if (expect.TryGetProperty("type", out var type)) Assert.Equal(type.GetString(), got.Type);
        if (expect.TryGetProperty("id", out var id)) Assert.Equal(id.GetString(), got.Id);
    }

    [Fact]
    public void Refuses_to_run_without_an_auth_token() =>
        Assert.Throws<ArgumentException>(() => TwilioWebhooks.Verify([], [], "https://example.test/", ""));

    [Fact]
    public void Passes_on_the_idempotency_token_of_a_retry()
    {
        var c = Find("retry carries the idempotency token");
        var got = TwilioWebhooks.Handle(Encoding.UTF8.GetBytes(c.GetProperty("body").GetString()!), Headers(c), c.GetProperty("url").GetString()!, Secret);
        Assert.Equal("test-idem-1", got.IdempotencyToken);
    }
}
