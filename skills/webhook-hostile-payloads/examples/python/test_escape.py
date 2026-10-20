"""The expected outputs in ../fixtures/cases.json were written by hand from each destination's
documented rules, so these tests check the code against the documentation.

    python -m unittest -v test_escape.py
"""

import json
import os
import unittest

from escape import discord_message, html_escape, log_safe, slack_escape, telegram_html_escape, telegram_markdown_v2_escape

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fixtures", "cases.json"), encoding="utf-8") as f:
    CASES = json.load(f)

FUNCTIONS = {
    "slack": slack_escape,
    "telegramMarkdownV2": telegram_markdown_v2_escape,
    "telegramHtml": telegram_html_escape,
    "html": html_escape,
    "log": log_safe,
}


class Escaping(unittest.TestCase):
    def test_every_documented_case(self):
        for name, fn in FUNCTIONS.items():
            for given, expected in CASES[name]:
                with self.subTest(name=name, given=given):
                    self.assertEqual(fn(given), expected)

    def test_discord_suppresses_mentions_and_embeds_and_fits_the_limit(self):
        msg = discord_message("@everyone <@&123> look at https://evil.example " + "x" * 3000)
        self.assertEqual(msg["allowed_mentions"], {"parse": []})
        self.assertEqual(msg["flags"], 4)
        self.assertEqual(len(msg["content"]), 2000)
        self.assertTrue(msg["content"].startswith("@everyone <@&123>"))
        self.assertEqual(discord_message("short")["content"], "short")

    def test_escaping_twice_is_visible(self):
        self.assertEqual(slack_escape(slack_escape("<!here>")), "&amp;lt;!here&amp;gt;")


if __name__ == "__main__":
    unittest.main()
