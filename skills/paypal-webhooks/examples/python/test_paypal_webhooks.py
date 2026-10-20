"""Runs every case in ../fixtures/vectors.json (made with the openssl command line) against
paypal_webhooks.py. fetch_certificate answers from the vectors' certificates and raises for any URL
not listed there, so a request that reaches the network for a URL the rule should have refused fails
the test."""

import json
import os
import unittest
import zlib

from paypal_webhooks import handle, is_trusted_certificate_url, verify

with open(os.path.join(os.path.dirname(__file__), "..", "fixtures", "vectors.json"), encoding="utf-8") as f:
    VECTORS = json.load(f)


def fetch_certificate(url):
    try:
        return VECTORS["config"]["certificates"][url]
    except KeyError:
        raise RuntimeError(f"no certificate for {url}")


OPTIONS = {"webhook_id": VECTORS["config"]["webhookId"], "fetch_certificate": fetch_certificate}


class PayPalVectors(unittest.TestCase):
    def test_every_case(self):
        for c in VECTORS["cases"]:
            with self.subTest(c["name"]):
                if c.get("verifyOnly"):
                    self.assertEqual(verify(c["body"], c["headers"], **OPTIONS), c["expect"]["verified"])
                    continue
                got = handle(c["body"].encode("utf-8"), c["headers"], **OPTIONS)
                self.assertEqual({k: got.get(k) for k in c["expect"]}, c["expect"])

    def test_refuses_to_run_without_a_webhook_id(self):
        with self.assertRaises(ValueError):
            verify(b"{}", {}, webhook_id="", fetch_certificate=fetch_certificate)

    def test_refuses_to_run_without_a_certificate_fetcher(self):
        with self.assertRaises(ValueError):
            handle(b"{}", {}, webhook_id="x", fetch_certificate=None)

    def test_crc32_matches_the_standard_check_value(self):
        self.assertEqual(zlib.crc32(b"123456789"), 0xCBF43926)

    def test_certificate_url_rule(self):
        self.assertTrue(is_trusted_certificate_url("https://api.paypal.com/v1/notifications/certs/C"))
        self.assertTrue(is_trusted_certificate_url("https://paypal.com/c"))
        self.assertFalse(is_trusted_certificate_url("https://evilpaypal.com/c"))
        self.assertFalse(is_trusted_certificate_url("https://paypal.com@evil.test/c"))
        self.assertFalse(is_trusted_certificate_url("https://user:pw@api.paypal.com/c"))
        self.assertFalse(is_trusted_certificate_url("https://api.paypal.com:8443/c"))
        self.assertFalse(is_trusted_certificate_url("http://api.paypal.com/c"))
        self.assertFalse(is_trusted_certificate_url("https://evil.test\\.paypal.com/c"))
        self.assertFalse(is_trusted_certificate_url("not a url"))


if __name__ == "__main__":
    unittest.main()
