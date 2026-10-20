"""Runs every case in ../fixtures/vectors.json (made with the openssl command line) against
shopify_webhooks.py."""

import json
import os
import unittest

from shopify_webhooks import handle, verify

with open(os.path.join(os.path.dirname(__file__), "..", "fixtures", "vectors.json"), encoding="utf-8") as f:
    VECTORS = json.load(f)


class ShopifyVectors(unittest.TestCase):
    def test_every_case(self):
        for c in VECTORS["cases"]:
            with self.subTest(c["name"]):
                if c.get("verifyOnly"):
                    self.assertEqual(verify(c["body"], c["headers"], c["secret"]), c["expect"]["verified"])
                    continue
                got = handle(c["body"].encode("utf-8"), c["headers"], VECTORS["config"]["secret"])
                self.assertEqual({k: got.get(k) for k in c["expect"]}, c["expect"])

    def test_returns_the_event_id_and_shop_domain(self):
        c = next(x for x in VECTORS["cases"] if x["name"] == "orders/create")
        got = handle(c["body"].encode("utf-8"), c["headers"], VECTORS["config"]["secret"])
        self.assertEqual(got["eventId"], c["headers"]["X-Shopify-Event-Id"])
        self.assertEqual(got["shop"], c["headers"]["X-Shopify-Shop-Domain"])

    def test_refuses_to_run_without_a_secret(self):
        with self.assertRaises(ValueError):
            verify(b"{}", {}, "")


if __name__ == "__main__":
    unittest.main()
