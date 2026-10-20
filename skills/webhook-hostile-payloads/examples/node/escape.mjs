// Escaping untrusted webhook text for the places it ends up. Each function implements only what the
// destination documents (rules and read dates in ../fixtures/cases.json). No dependencies.
//
// Text in a webhook payload is written by whoever the sender lets write it: a customer name, an order
// note, a commit message. A valid signature proves who SENT it, not that the text is safe.

/** Slack mrkdwn: & < > are control characters; replace exactly those (Slack: "Escaping text"). */
export function slackEscape(text) {
  return String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

const MARKDOWN_V2 = /[_*\[\]()~`>#+\-=|{}.!\\]/g;

/** Telegram MarkdownV2: backslash before each of _ * [ ] ( ) ~ ` > # + - = | { } . ! and before backslash. */
export function telegramMarkdownV2Escape(text) {
  return String(text).replace(MARKDOWN_V2, (c) => "\\" + c);
}

/** Telegram HTML parse mode: replace < > & that are not part of a tag or entity (all of them, for payload text). */
export function telegramHtmlEscape(text) {
  return String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/** HTML text and attribute values. */
export function htmlEscape(text) {
  return String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

/**
 * One log line: control characters (including CR, LF and tab) and the Unicode line and paragraph
 * separators become visible escapes, so payload text cannot start a forged log entry.
 */
export function logSafe(text) {
  return String(text).replace(/[\u0000-\u001f\u007f\u2028\u2029]/g, (c) => {
    if (c === "\n") return "\\n";
    if (c === "\r") return "\\r";
    if (c === "\t") return "\\t";
    return "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0");
  });
}

const DISCORD_CONTENT_MAX = 2000;
const SUPPRESS_EMBEDS = 1 << 2;

/**
 * A Discord execute-webhook body that cannot ping anyone or unfurl a link: allowed_mentions with an
 * empty parse list suppresses @everyone, @here, role and user mentions; SUPPRESS_EMBEDS stops link
 * previews. Content is cut to Discord's 2000-character limit.
 */
export function discordMessage(text) {
  const content = String(text);
  return {
    content: content.length > DISCORD_CONTENT_MAX ? content.slice(0, DISCORD_CONTENT_MAX - 1) + "…" : content,
    allowed_mentions: { parse: [] },
    flags: SUPPRESS_EMBEDS,
  };
}
