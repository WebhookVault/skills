// Escaping untrusted webhook text for the places it ends up. Each method implements only what the
// destination documents (rules and read dates in ../fixtures/cases.json). Base library only.
//
// Text in a webhook payload is written by whoever the sender lets write it: a customer name, an order
// note, a commit message. A valid signature proves who SENT it, not that the text is safe.

using System.Text;
using System.Text.RegularExpressions;

namespace WebhookHostilePayloads;

public sealed record DiscordAllowedMentions(string[] Parse);

public sealed record DiscordMessage(string Content, DiscordAllowedMentions AllowedMentions, int Flags);

public static partial class Escape
{
    public const int DiscordContentMax = 2000;
    public const int SuppressEmbeds = 1 << 2;

    /// <summary>Slack mrkdwn: &amp; &lt; &gt; are control characters; replace exactly those.</summary>
    public static string Slack(string text) => text.Replace("&", "&amp;").Replace("<", "&lt;").Replace(">", "&gt;");

    [GeneratedRegex(@"[_*\[\]()~`>#+\-=|{}.!\\]")] private static partial Regex MarkdownV2Special();

    /// <summary>Telegram MarkdownV2: a backslash before each of _ * [ ] ( ) ~ ` &gt; # + - = | { } . ! and backslash.</summary>
    public static string TelegramMarkdownV2(string text) => MarkdownV2Special().Replace(text, m => "\\" + m.Value);

    /// <summary>Telegram HTML parse mode: replace &lt; &gt; &amp; (all of them, for payload text).</summary>
    public static string TelegramHtml(string text) => text.Replace("&", "&amp;").Replace("<", "&lt;").Replace(">", "&gt;");

    /// <summary>HTML text and attribute values.</summary>
    public static string Html(string text)
        => text.Replace("&", "&amp;").Replace("<", "&lt;").Replace(">", "&gt;").Replace("\"", "&quot;").Replace("'", "&#39;");

    /// <summary>One log line: control characters and the Unicode line and paragraph separators become visible escapes.</summary>
    public static string LogSafe(string text)
    {
        var sb = new StringBuilder(text.Length);
        foreach (var c in text)
        {
            if (c == '\n') sb.Append("\\n");
            else if (c == '\r') sb.Append("\\r");
            else if (c == '\t') sb.Append("\\t");
            else if (c < 0x20 || c == 0x7F || c == '\u2028' || c == '\u2029') sb.Append("\\u").Append(((int)c).ToString("x4"));
            else sb.Append(c);
        }
        return sb.ToString();
    }

    /// <summary>A Discord execute-webhook body that cannot ping anyone or unfurl a link (serialise with snake_case names).</summary>
    public static DiscordMessage Discord(string text)
    {
        var content = text.Length > DiscordContentMax ? text[..(DiscordContentMax - 1)] + "…" : text;
        return new DiscordMessage(content, new DiscordAllowedMentions([]), SuppressEmbeds);
    }
}
