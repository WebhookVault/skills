// The expected outputs in ../fixtures/cases.json were written by hand from each destination's
// documented rules, so these tests check the code against the documentation.

using System.Text.Json;
using Xunit;

namespace WebhookHostilePayloads;

public class EscapeTests
{
    private static readonly JsonElement Cases =
        JsonDocument.Parse(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "fixtures", "cases.json"))).RootElement;

    private static readonly Dictionary<string, Func<string, string>> Functions = new()
    {
        ["slack"] = Escape.Slack,
        ["telegramMarkdownV2"] = Escape.TelegramMarkdownV2,
        ["telegramHtml"] = Escape.TelegramHtml,
        ["html"] = Escape.Html,
        ["log"] = Escape.LogSafe,
    };

    public static TheoryData<string, string, string> Documented()
    {
        var data = new TheoryData<string, string, string>();
        foreach (var name in Functions.Keys)
            foreach (var pair in Cases.GetProperty(name).EnumerateArray())
                data.Add(name, pair[0].GetString()!, pair[1].GetString()!);
        return data;
    }

    [Theory, MemberData(nameof(Documented))]
    public void every_documented_case(string name, string given, string expected) => Assert.Equal(expected, Functions[name](given));

    [Fact]
    public void discord_suppresses_mentions_and_embeds_and_fits_the_limit()
    {
        var msg = Escape.Discord("@everyone <@&123> look at https://evil.example " + new string('x', 3000));
        Assert.Empty(msg.AllowedMentions.Parse);
        Assert.Equal(4, msg.Flags);
        Assert.Equal(2000, msg.Content.Length);
        Assert.StartsWith("@everyone <@&123>", msg.Content);
        Assert.Equal("short", Escape.Discord("short").Content);

        var json = JsonSerializer.Serialize(msg, new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower });
        Assert.Contains("\"allowed_mentions\":{\"parse\":[]}", json);
    }

    [Fact]
    public void escaping_twice_is_visible() => Assert.Equal("&amp;lt;!here&amp;gt;", Escape.Slack(Escape.Slack("<!here>")));
}
