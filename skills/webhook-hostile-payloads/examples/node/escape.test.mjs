// The expected outputs in ../fixtures/cases.json were written by hand from each destination's
// documented rules, so these tests check the code against the documentation, not against itself.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { slackEscape, telegramMarkdownV2Escape, telegramHtmlEscape, htmlEscape, logSafe, discordMessage } from "./escape.mjs";

const cases = JSON.parse(readFileSync(new URL("../fixtures/cases.json", import.meta.url), "utf8"));
const fns = { slack: slackEscape, telegramMarkdownV2: telegramMarkdownV2Escape, telegramHtml: telegramHtmlEscape, html: htmlEscape, log: logSafe };

for (const [name, fn] of Object.entries(fns)) {
  for (const [input, expected] of cases[name]) {
    test(`${name}: ${JSON.stringify(input)}`, () => assert.equal(fn(input), expected));
  }
}

test("Discord: mentions and embeds are suppressed and content fits the limit", () => {
  const msg = discordMessage("@everyone <@&123> look at https://evil.example " + "x".repeat(3000));
  assert.deepEqual(msg.allowed_mentions, { parse: [] });
  assert.equal(msg.flags, 4);
  assert.equal(msg.content.length, 2000);
  assert.ok(msg.content.startsWith("@everyone <@&123>"), "the text itself is kept; only its effect is suppressed");
  assert.equal(discordMessage("short").content, "short");
});

test("escaping twice is visible, so escape exactly once at the point of output", () => {
  assert.equal(slackEscape(slackEscape("<!here>")), "&amp;lt;!here&amp;gt;");
});
