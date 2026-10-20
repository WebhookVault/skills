# Putting payload text into chat messages

## Contents

- Slack
- Discord
- Microsoft Teams
- Telegram
- What the vendors do not document

Read from each vendor's own documentation on 2026-10-20. Vendors change their formatting rules; re-read
the linked pages before relying on a detail.

## Slack

Source: https://docs.slack.dev/messaging/formatting-message-text and
https://docs.slack.dev/reference/block-kit/composition-objects/text-object

- `&`, `<` and `>` are control characters. Replace them with `&amp;`, `&lt;` and `&gt;` when they are
  not meant for parsing. Slack says to replace only those, not to encode the whole text.
- Mentions and links are angle-bracket markup: users `<@U...>`, channels `<#C...>`, user groups
  `<!subteam^...>`, and `<!here>`, `<!channel>`, `<!everyone>`. Escaping `<` keeps payload text from
  forming any of them.
- Auto-linking of names happens when `link_names` is sent with top-level `text`; leave it out. For
  layout blocks, set `verbatim: true` on `mrkdwn` text objects. `parse: none` also stops plain URLs
  becoming links.
- Text objects are `plain_text` or `mrkdwn`; `verbatim` applies only to `mrkdwn`.

## Discord

Source: https://docs.discord.com/developers/resources/message and
https://docs.discord.com/developers/resources/webhook (the older discord.com/developers/docs addresses
redirect there)

- `allowed_mentions` decides who can be notified. `{"parse": []}` allows no mention types at all, so
  `@everyone`, `@here`, role and user mentions in the text notify no one. `parse` cannot be combined
  with `users` or `roles` lists in one request.
- Execute webhook accepts the flags `SUPPRESS_EMBEDS` (`1 << 2`, no link previews) and
  `SUPPRESS_NOTIFICATIONS` (`1 << 12`).
- `content` is at most 2000 characters.
- Discord renders a subset of markdown and documents no escaping mechanism for it. Suppressing
  mentions and embeds is the documented defence.

## Microsoft Teams

Source: https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook
and https://learn.microsoft.com/en-us/adaptive-cards/authoring-cards/text-features

- Microsoft 365 Connectors (formerly Office 365 Connectors) are nearing deprecation; Microsoft points
  to Workflows with the "When a Teams webhook request is received" trigger, which accepts Adaptive
  Cards. Messages are limited to 28 KB, and more than four requests a second are throttled.
- An Adaptive Card `TextBlock` renders a subset of CommonMark: bold, italic, lists and links.
  Microsoft documents no way to show those characters literally in a `TextBlock`.
- `RichTextBlock` does not support markdown; its `TextRun` elements carry plain text with formatting
  set as properties. Use it for payload text.

## Telegram

Source: https://core.telegram.org/bots/api#formatting-options

- `sendMessage` takes an optional `parse_mode`: `MarkdownV2`, `HTML` or the legacy `Markdown`. Send
  payload text without a parse mode, or with formatting given as `entities`.
- MarkdownV2: each of these 18 characters must be escaped with a backslash, and a backslash itself is
  escaped with a backslash:

  ```
  _ * [ ] ( ) ~ ` > # + - = | { } . !
  ```
 Inside `pre` and `code`, backtick and backslash must
  be escaped; inside a link's URL part, `)` and backslash.
- HTML: every `<`, `>` and `&` that is not part of a tag or entity is replaced with `&lt;`, `&gt;` and
  `&amp;`. Only a few named entities are supported.

## What the vendors do not document

- Slack: whether `plain_text` objects parse mention markup, and how to escape `*`, `_`, `` ` ``, `~`.
- Discord: any markdown escaping.
- Teams: any escaping inside a `TextBlock`, and mention behaviour of payload text.

Where a vendor documents nothing, prefer the structural option (plain text, no parse mode, mentions
suppressed) over an escaping scheme of your own invention.
