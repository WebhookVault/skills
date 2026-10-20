"""Runs every case in ../fixtures/vectors.json (made with the openssl command line, plus Twilio's own
published example) against twilio_webhooks.py."""

import json
import os
import unittest

from twilio_webhooks import handle, verify

with open(os.path.join(os.path.dirname(__file__), "..", "fixtures", "vectors.json"), encoding="utf-8") as f:
    VECTORS = json.load(f)


class TwilioVectors(unittest.TestCase):
    def test_every_case(self):
        for c in VECTORS["cases"]:
            with self.subTest(c["name"]):
                if c.get("verifyOnly"):
                    self.assertEqual(verify(c["body"], c["headers"], c["url"], c["secret"]), c["expect"]["verified"])
                    continue
                got = handle(c["body"].encode("utf-8"), c["headers"], c["url"], VECTORS["config"]["secret"])
                self.assertEqual({k: got.get(k) for k in c["expect"]}, c["expect"])

    def test_refuses_to_run_without_an_auth_token(self):
        with self.assertRaises(ValueError):
            verify(b"", {}, "https://example.test/", "")

    def test_passes_on_the_idempotency_token_of_a_retry(self):
        c = next(x for x in VECTORS["cases"] if "I-Twilio-Idempotency-Token" in x["headers"])
        got = handle(c["body"].encode("utf-8"), c["headers"], c["url"], VECTORS["config"]["secret"])
        self.assertEqual(got["idempotencyToken"], c["headers"]["I-Twilio-Idempotency-Token"])


if __name__ == "__main__":
    unittest.main()
