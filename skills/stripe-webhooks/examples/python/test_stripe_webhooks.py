"""Runs every case in ../fixtures/vectors.json (made with the openssl command line) against
stripe_webhooks.py."""

import json
import os
import unittest

from stripe_webhooks import handle, verify

with open(os.path.join(os.path.dirname(__file__), "..", "fixtures", "vectors.json"), encoding="utf-8") as f:
    VECTORS = json.load(f)

TOLERANCE = VECTORS["config"]["toleranceSeconds"]


class StripeVectors(unittest.TestCase):
    def test_every_case(self):
        for c in VECTORS["cases"]:
            with self.subTest(c["name"]):
                if c.get("verifyOnly"):
                    self.assertEqual(verify(c["body"], c["headers"], c["secret"], c["now"], TOLERANCE), c["expect"]["verified"])
                    continue
                got = handle(c["body"].encode("utf-8"), c["headers"], VECTORS["config"]["secret"], c["now"], TOLERANCE)
                self.assertEqual({k: got.get(k) for k in c["expect"]}, c["expect"])

    def test_refuses_to_run_without_a_secret(self):
        with self.assertRaises(ValueError):
            verify(b"{}", {}, "")


if __name__ == "__main__":
    unittest.main()
