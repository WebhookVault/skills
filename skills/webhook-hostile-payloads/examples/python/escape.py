"""Escaping untrusted webhook text for the places it ends up. Each function implements only what the
destination documents (rules and read dates in ../fixtures/cases.json). Standard library only.

Text in a webhook payload is written by whoever the sender lets write it: a customer name, an order
note, a commit message. A valid signature proves who SENT it, not that the text is safe.
"""

import re

_MARKDOWN_V2 = re.compile(r"([_*\[\]()~`>#+\-=|{}.!\\])")
_LOG_UNSAFE = re.compile("[\x00-\x1f\x7f\u2028\u2029]")
DISCORD_CONTENT_MAX = 2000
SUPPRESS_EMBEDS = 1 << 2


def slack_escape(text: str) -> str:
    """Slack mrkdwn: & < > are control characters; replace exactly those (Slack: "Escaping text")."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def telegram_markdown_v2_escape(text: str) -> str:
    """Telegram MarkdownV2: a backslash before each of _ * [ ] ( ) ~ ` > # + - = | { } . ! and backslash."""
    return _MARKDOWN_V2.sub(r"\\\1", str(text))


def telegram_html_escape(text: str) -> str:
    """Telegram HTML parse mode: replace < > & (all of them, for payload text)."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def html_escape(text: str) -> str:
    """HTML text and attribute values."""
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def log_safe(text: str) -> str:
    """One log line: control characters and the Unicode line and paragraph separators become visible
    escapes, so payload text cannot start a forged log entry."""
    named = {"\n": "\\n", "\r": "\\r", "\t": "\\t"}
    return _LOG_UNSAFE.sub(lambda m: named.get(m.group(), "\\u%04x" % ord(m.group())), str(text))


def discord_message(text: str) -> dict:
    """A Discord execute-webhook body that cannot ping anyone or unfurl a link."""
    content = str(text)
    if len(content) > DISCORD_CONTENT_MAX:
        content = content[: DISCORD_CONTENT_MAX - 1] + "…"
    return {"content": content, "allowed_mentions": {"parse": []}, "flags": SUPPRESS_EMBEDS}
