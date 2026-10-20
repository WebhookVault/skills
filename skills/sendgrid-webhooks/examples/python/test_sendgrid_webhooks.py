"""Runs every case in ../fixtures/vectors.json (signed by the openssl command line with a P-256 key
made for that run) against sendgrid_webhooks.py."""

import json
import os
import unittest

from sendgrid_webhooks import handle, load_public_key

with open(os.path.join(os.path.dirname(__file__), "..", "fixtures", "vectors.json"), encoding="utf-8") as f:
    VECTORS = json.load(f)


class SendGridVectors(unittest.TestCase):
    def test_every_case(self):
        key = load_public_key(VECTORS["config"]["publicKey"])
        for c in VECTORS["cases"]:
            with self.subTest(c["name"]):
                got = handle(c["body"].encode("utf-8"), c["headers"], key)
                self.assertEqual({k: got.get(k) for k in c["expect"]}, c["expect"])

    def test_refuses_to_run_without_a_key(self):
        with self.assertRaises(ValueError):
            load_public_key("")


if __name__ == "__main__":
    unittest.main()
