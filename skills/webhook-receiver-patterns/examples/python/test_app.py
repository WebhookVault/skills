"""Drives the receiver through FastAPI's TestClient. Signatures are made with the openssl command
line, not with the code under test.

    python -m unittest -v test_app.py
"""

import subprocess
import unittest

from fastapi.testclient import TestClient

from app import MAX_BODY_BYTES, create_app

SECRET = "test-receiver-secret"
NOW = 1760000000


def openssl_sign(t: int, body: bytes) -> str:
    out = subprocess.run(["openssl", "dgst", "-sha256", "-hmac", SECRET, "-hex"], input=f"{t}.".encode() + body,
                         capture_output=True, check=True).stdout.decode()
    return out.strip().split()[-1]


class Receiver(unittest.TestCase):
    def setUp(self):
        self.queued = []
        self.fail_next = False

        async def enqueue(event):
            if self.fail_next:
                self.fail_next = False
                raise RuntimeError("queue down")
            self.queued.append(event["id"])

        self.client = TestClient(create_app(SECRET, enqueue, now=lambda: NOW))

    def post(self, body: bytes, t=NOW, signature=None, headers=None):
        sig = signature if signature is not None else f"t={t},v1={openssl_sign(t, body)}"
        h = {"Content-Type": "application/json", "Webhook-Signature": sig, **(headers or {})}
        return self.client.post("/webhooks", content=body, headers=h)

    def test_a_signed_event_is_acknowledged_and_queued_once(self):
        res = self.post(b'{"id":"evt_test_a","type":"order.created"}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"received": True})
        self.assertEqual(self.queued, ["evt_test_a"])

    def test_the_same_event_again_is_acknowledged_and_not_queued_twice(self):
        self.post(b'{"id":"evt_test_b"}')
        res = self.post(b'{"id":"evt_test_b"}')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["duplicate"])
        self.assertEqual(self.queued, ["evt_test_b"])

    def test_a_wrong_signature_is_refused_and_nothing_is_queued(self):
        res = self.post(b'{"id":"evt_test_c"}', signature=f"t={NOW},v1={'0' * 64}")
        self.assertEqual(res.status_code, 401)
        self.assertEqual(self.queued, [])

    def test_an_unverified_request_does_not_use_up_the_event_id(self):
        self.post(b'{"id":"evt_test_d"}', signature="t=1,v1=bad")
        res = self.post(b'{"id":"evt_test_d"}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.queued, ["evt_test_d"])

    def test_a_stale_timestamp_is_refused(self):
        self.assertEqual(self.post(b'{"id":"evt_test_e"}', t=NOW - 3600).status_code, 401)

    def test_a_missing_signature_header_is_refused(self):
        res = self.client.post("/webhooks", content=b'{"id":"evt_test_f"}', headers={"Content-Type": "application/json"})
        self.assertEqual(res.status_code, 401)

    def test_a_signed_body_that_is_not_json_is_refused_with_400(self):
        res = self.post(b"not json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["error"], "invalid_json")

    def test_a_signed_event_without_an_id_is_refused(self):
        self.assertEqual(self.post(b'{"type":"order.created"}').status_code, 400)

    def test_a_body_over_the_limit_is_refused_with_413(self):
        big = b'{"id":"evt_test_big","pad":"' + b"x" * MAX_BODY_BYTES + b'"}'
        self.assertEqual(self.post(big).status_code, 413)

    def test_a_failed_hand_off_answers_500(self):
        self.fail_next = True
        self.assertEqual(self.post(b'{"id":"evt_test_g"}').status_code, 500)

    def test_the_signature_covers_the_exact_bytes(self):
        signed_body = b'{"id":"evt_test_h"}'
        sig = "t=%d,v1=%s" % (NOW, openssl_sign(NOW, signed_body))
        self.assertEqual(self.post(b'{ "id": "evt_test_h" }', signature=sig).status_code, 401)


if __name__ == "__main__":
    unittest.main()
