"""Runs every case in ../fixtures/vectors.json (signed with an Ed25519 key made for that run by the
openssl command line) against discord_webhooks.py."""

import json
import os
import unittest

from discord_webhooks import handle_event, handle_interaction, verify

with open(os.path.join(os.path.dirname(__file__), "..", "fixtures", "vectors.json"), encoding="utf-8") as f:
    VECTORS = json.load(f)
PUBLIC_KEY = VECTORS["config"]["publicKey"]


class DiscordVectors(unittest.TestCase):
    def test_every_case(self):
        for c in VECTORS["cases"]:
            with self.subTest(c["name"]):
                if c.get("verifyOnly"):
                    self.assertEqual(verify(c["body"], c["headers"], PUBLIC_KEY), c["expect"]["verified"])
                    continue
                run = handle_event if c["mechanism"] == "events" else handle_interaction
                got = run(c["body"].encode("utf-8"), c["headers"], PUBLIC_KEY)
                self.assertEqual({k: got.get(k) for k in c["expect"]}, c["expect"])

    def test_refuses_to_run_without_a_public_key(self):
        with self.assertRaises(ValueError):
            verify(b"{}", {}, "")


if __name__ == "__main__":
    unittest.main()
