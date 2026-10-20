// Runs every case in ../fixtures/vectors.json (signed by the openssl command line with a P-256 key
// made for that run) against SendGridWebhooks.cs.

using System.Text;
using System.Text.Json;
using SendGridWebhooksExample;
using Xunit;

public class SendGridWebhooksTests
{
    static readonly JsonElement Vectors = JsonDocument.Parse(File.ReadAllText(
        Path.Combine(AppContext.BaseDirectory, "fixtures", "vectors.json"))).RootElement;

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
        using var key = SendGridWebhooks.LoadPublicKey(Vectors.GetProperty("config").GetProperty("publicKey").GetString()!);
        var expect = c.GetProperty("expect");

        var got = SendGridWebhooks.Handle(Encoding.UTF8.GetBytes(c.GetProperty("body").GetString()!), headers, key);
        Assert.Equal(expect.GetProperty("status").GetInt32(), got.Status);
        if (expect.TryGetProperty("events", out var events))
        {
            var want = events.EnumerateArray().Select(e => new SendGridEvent(e.GetProperty("type").GetString(), e.GetProperty("id").GetString())).ToList();
            Assert.Equal(want, got.Events);
        }
    }

    [Fact]
    public void Refuses_to_run_without_a_key() =>
        Assert.Throws<ArgumentException>(() => SendGridWebhooks.LoadPublicKey(""));
}
