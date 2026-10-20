"""Checks verify.py against ../fixtures/vectors.json, which the openssl command line signed
(make_vectors.py), and against the failure cases every verifier must reject.

    python -m unittest -v test_verify.py
"""

import base64
import json
import os
import unittest

import verify as v

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "..", "fixtures", "vectors.json"), encoding="utf-8") as f:
    VECTORS = json.load(f)


def raw(vec):
    return vec["body"].encode("utf-8")


def call(vec, **o):
    """Verifies one vector, with any field overridden by `o`."""
    body = o.get("body", raw(vec)) if "body" in vec else None
    fam = vec["family"]
    if fam == "hmac-body":
        return v.verify_hmac_body(body, o.get("signature", vec["signature"]), o.get("secret", vec["secret"]), vec["encoding"], vec["prefix"])
    if fam == "hmac-timestamp-header":
        return v.verify_timestamp_header(body, o.get("header", vec["header"]), o.get("secret", vec["secret"]), o.get("now", vec["now"]),
                                         vec["tolerance"], vec["pairSeparator"], vec["timestampKey"], vec["signatureKey"], vec["joiner"])
    if fam == "hmac-versioned-timestamp":
        return v.verify_versioned_timestamp(body, vec["timestamp"], o.get("signature", vec["signature"]), o.get("secret", vec["secret"]),
                                            o.get("now", vec["now"]), vec["tolerance"])
    if fam == "standard-webhooks":
        return v.verify_standard_webhooks(body, vec["id"], vec["timestamp"], o.get("signature", vec["signature"]), o.get("secret", vec["secret"]),
                                          o.get("now", vec["now"]), vec["tolerance"])
    if fam == "hmac-url-form":
        return v.verify_url_form(o.get("url", vec["url"]), vec["params"], o.get("signature", vec["signature"]), o.get("secret", vec["secret"]))
    if fam == "ed25519":
        return v.verify_ed25519(body, vec["timestamp"], o.get("signature", vec["signature"]), vec["publicKey"], o.get("now", vec["now"]), vec["tolerance"])
    if fam == "ecdsa-p256":
        return v.verify_ecdsa_p256(body, vec["timestamp"], o.get("signature", vec["signature"]), vec["publicKey"], o.get("now", vec["now"]), vec["tolerance"])
    if fam == "shared-token":
        return v.verify_shared_token(o.get("signature", vec["signature"]), o.get("secret", vec["secret"]))
    raise AssertionError(f"no test mapping for family {fam}")


WRONG_SECRET = {
    "hmac-body": "test-wrong-secret",
    "hmac-timestamp-header": "test-wrong-secret",
    "hmac-versioned-timestamp": "test-wrong-secret",
    "standard-webhooks": "whsec_" + base64.b64encode(bytes([7]) * 32).decode(),
    "hmac-url-form": "test-wrong-token",
    "shared-token": "test-other-token",
}
TIMED = {"hmac-timestamp-header", "hmac-versioned-timestamp", "standard-webhooks", "ed25519", "ecdsa-p256"}


class Vectors(unittest.TestCase):
    def test_every_openssl_signature_verifies(self):
        for vec in VECTORS:
            with self.subTest(vec["family"] + " " + vec["name"]):
                self.assertTrue(call(vec))

    def test_one_changed_byte_in_the_body_is_rejected(self):
        for vec in (x for x in VECTORS if "body" in x):
            with self.subTest(vec["family"] + " " + vec["name"]):
                self.assertFalse(call(vec, body=raw(vec) + b" "))

    def test_a_reserialised_json_body_is_rejected_unless_identical(self):
        for vec in (x for x in VECTORS if x.get("body", "").startswith("{")):
            reserialised = json.dumps(json.loads(vec["body"]), indent=2).encode("utf-8")
            if reserialised == raw(vec):
                continue
            with self.subTest(vec["family"] + " " + vec["name"]):
                self.assertFalse(call(vec, body=reserialised))

    def test_the_wrong_secret_is_rejected(self):
        for vec in (x for x in VECTORS if x["family"] in WRONG_SECRET):
            with self.subTest(vec["family"] + " " + vec["name"]):
                self.assertFalse(call(vec, secret=WRONG_SECRET[vec["family"]]))

    def test_a_timestamp_outside_the_tolerance_is_rejected(self):
        for vec in (x for x in VECTORS if x["family"] in TIMED):
            with self.subTest(vec["family"] + " " + vec["name"]):
                self.assertFalse(call(vec, now=vec["now"] + 10_000))

    def test_missing_and_garbage_signatures_are_rejected_without_raising(self):
        for vec in VECTORS:
            field = "header" if vec["family"] == "hmac-timestamp-header" else "signature"
            for bad in (None, "", "%%%not-a-signature%%%", "nonsense;;==,,"):
                with self.subTest(vec["family"] + " " + vec["name"] + " " + repr(bad)):
                    self.assertFalse(call(vec, **{field: bad}))


with open(os.path.join(HERE, "..", "fixtures", "published.json"), encoding="utf-8") as f:
    PUBLISHED = json.load(f)


class Published(unittest.TestCase):
    """The providers' own published examples (GitHub and Slack documentation, the Standard
    Webhooks library tests), copied exactly with their source and read date."""

    def test_each_published_example_verifies_and_a_changed_byte_does_not(self):
        for vec in PUBLISHED:
            with self.subTest(vec["name"]):
                self.assertTrue(call(vec))
                self.assertFalse(call(vec, body=raw(vec) + b" "))


class SignRequestScript(unittest.TestCase):
    """scripts/sign_request.py must produce headers these verifiers accept."""

    def run_script(self, family, secret, body):
        import subprocess
        import sys
        import tempfile
        import time
        script = os.path.join(HERE, "..", "..", "scripts", "sign_request.py")
        with tempfile.NamedTemporaryFile("wb", delete=False, suffix=".json") as f:
            f.write(body)
        try:
            out = subprocess.run([sys.executable, script, family, f.name], capture_output=True, text=True, check=True,
                                 env={**os.environ, "WEBHOOK_TEST_SECRET": secret}).stdout
        finally:
            os.unlink(f.name)
        headers = dict(line.split(": ", 1) for line in out.strip().splitlines())
        return headers, int(time.time())

    def test_each_family_it_signs_verifies(self):
        body = '{"id":"evt_test","note":"café"}'.encode("utf-8")
        h, now = self.run_script("hmac-body", "test-secret", body)
        self.assertTrue(v.verify_hmac_body(body, h["X-Signature"], "test-secret", "hex", "sha256="))
        h, now = self.run_script("timestamp-header", "test-secret", body)
        self.assertTrue(v.verify_timestamp_header(body, h["X-Signature"], "test-secret", now))
        h, now = self.run_script("versioned-timestamp", "test-secret", body)
        self.assertTrue(v.verify_versioned_timestamp(body, h["X-Timestamp"], h["X-Signature"], "test-secret", now))
        secret = "whsec_" + base64.b64encode(bytes(range(32))).decode()
        h, now = self.run_script("standard-webhooks", secret, body)
        self.assertTrue(v.verify_standard_webhooks(body, h["webhook-id"], h["webhook-timestamp"], h["webhook-signature"], secret, now))


class Edges(unittest.TestCase):
    def test_a_url_rebuilt_behind_a_proxy_fails(self):
        vec = next(x for x in VECTORS if x["family"] == "hmac-url-form")
        self.assertFalse(call(vec, url=vec["url"].replace("https://", "http://")))

    def test_a_header_with_two_timestamps_is_rejected(self):
        vec = next(x for x in VECTORS if x["family"] == "hmac-timestamp-header" and x["name"] == "comma-json")
        self.assertFalse(call(vec, header="t=1," + vec["header"]))

    def test_freshness(self):
        self.assertTrue(v.is_fresh("1000", 1200, 300))
        self.assertFalse(v.is_fresh("1000", 1301, 300))
        self.assertFalse(v.is_fresh("1000", 699, 300))
        self.assertFalse(v.is_fresh("1000.5", 1000, 300))
        self.assertFalse(v.is_fresh("", 1000, 300))
        self.assertFalse(v.is_fresh(None, 1000, 300))

    def test_safe_equal(self):
        self.assertFalse(v.safe_equal("abc", "abcd"))
        self.assertFalse(v.safe_equal(None, "a"))
        self.assertTrue(v.safe_equal("a", "a"))


if __name__ == "__main__":
    unittest.main()
