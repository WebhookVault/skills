// Runs every case in ../fixtures/vectors.json (signed with an Ed25519 key made for that run by the
// openssl command line) against DiscordWebhooks.cs.

using System.Text;
using System.Text.Json;
using DiscordWebhooksExample;
using Xunit;

public class DiscordWebhooksTests
{
    static readonly JsonElement Vectors = JsonDocument.Parse(File.ReadAllText(
        Path.Combine(AppContext.BaseDirectory, "fixtures", "vectors.json"))).RootElement;

    static string PublicKey => Vectors.GetProperty("config").GetProperty("publicKey").GetString()!;

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
            Assert.Equal(expect.GetProperty("verified").GetBoolean(), DiscordWebhooks.Verify(body, headers, PublicKey));
            return;
        }

        var got = c.GetProperty("mechanism").GetString() == "events"
            ? DiscordWebhooks.HandleEvent(body, headers, PublicKey)
            : DiscordWebhooks.HandleInteraction(body, headers, PublicKey);
        Assert.Equal(expect.GetProperty("status").GetInt32(), got.Status);
        // Interaction types are integers in the vectors and text in the result.
        if (expect.TryGetProperty("type", out var type))
            Assert.Equal(type.ValueKind == JsonValueKind.Number ? type.GetInt32().ToString() : type.GetString(), got.Type);
        if (expect.TryGetProperty("id", out var id)) Assert.Equal(id.ValueKind == JsonValueKind.Null ? null : id.GetString(), got.Id);
        if (expect.TryGetProperty("reply", out var reply)) Assert.Equal(reply.ValueKind == JsonValueKind.Null ? null : reply.GetString(), got.Reply);
    }

    [Fact]
    public void Refuses_to_run_without_a_public_key() =>
        Assert.Throws<ArgumentException>(() => DiscordWebhooks.Verify([], [], ""));
}
