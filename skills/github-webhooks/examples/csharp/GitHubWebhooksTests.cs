// Runs every case in ../fixtures/vectors.json (made with the openssl command line, plus GitHub's own
// published example) against GitHubWebhooks.cs.

using System.Text;
using System.Text.Json;
using GitHubWebhooksExample;
using Xunit;

public class GitHubWebhooksTests
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
        var body = Encoding.UTF8.GetBytes(c.GetProperty("body").GetString()!);
        var expect = c.GetProperty("expect");

        if (c.TryGetProperty("verifyOnly", out var vo) && vo.GetBoolean())
        {
            Assert.Equal(expect.GetProperty("verified").GetBoolean(), GitHubWebhooks.Verify(body, headers, c.GetProperty("secret").GetString()!));
            return;
        }

        var got = GitHubWebhooks.Handle(body, headers, Vectors.GetProperty("config").GetProperty("secret").GetString()!);
        Assert.Equal(expect.GetProperty("status").GetInt32(), got.Status);
        if (expect.TryGetProperty("type", out var type)) Assert.Equal(type.GetString(), got.Type);
        if (expect.TryGetProperty("action", out var action)) Assert.Equal(action.ValueKind == JsonValueKind.Null ? null : action.GetString(), got.Action);
        if (expect.TryGetProperty("id", out var id)) Assert.Equal(id.ValueKind == JsonValueKind.Null ? null : id.GetString(), got.Id);
    }

    [Fact]
    public void Refuses_to_run_without_a_secret() =>
        Assert.Throws<ArgumentException>(() => GitHubWebhooks.Verify([], [], ""));
}
