"""Signs a test request body so a receiver can be tested with a correct signature.

    WEBHOOK_TEST_SECRET=test-secret python sign_request.py hmac-body body.json
    WEBHOOK_TEST_SECRET=test-secret python sign_request.py timestamp-header body.json
    WEBHOOK_TEST_SECRET=whsec_<base64> python sign_request.py standard-webhooks body.json

Prints the headers to send. The body file is read as bytes and must be sent unchanged (for example
curl --data-binary @body.json). Use a test secret only: never a production secret.
Standard library only.
"""

import base64
import hashlib
import hmac
import os
import sys
import time
import uuid


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    family, path = sys.argv[1], sys.argv[2]
    secret = os.environ.get("WEBHOOK_TEST_SECRET")
    if not secret:
        sys.exit("Set WEBHOOK_TEST_SECRET to a test secret.")
    with open(path, "rb") as f:
        body = f.read()
    ts = str(int(time.time()))

    if family == "hmac-body":
        print("X-Signature: sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest())
    elif family == "timestamp-header":
        mac = hmac.new(secret.encode(), ts.encode() + b"." + body, hashlib.sha256).hexdigest()
        print(f"X-Signature: t={ts},v1={mac}")
    elif family == "versioned-timestamp":
        mac = hmac.new(secret.encode(), b"v0:" + ts.encode() + b":" + body, hashlib.sha256).hexdigest()
        print(f"X-Timestamp: {ts}")
        print(f"X-Signature: v0={mac}")
    elif family == "standard-webhooks":
        if not secret.startswith("whsec_"):
            sys.exit("A Standard Webhooks secret starts with whsec_.")
        key = base64.b64decode(secret[len("whsec_"):])
        msg_id = "msg_" + uuid.uuid4().hex
        mac = base64.b64encode(hmac.new(key, f"{msg_id}.{ts}.".encode() + body, hashlib.sha256).digest()).decode()
        print(f"webhook-id: {msg_id}")
        print(f"webhook-timestamp: {ts}")
        print(f"webhook-signature: v1,{mac}")
    else:
        sys.exit("family is one of: hmac-body, timestamp-header, versioned-timestamp, standard-webhooks")


if __name__ == "__main__":
    main()
