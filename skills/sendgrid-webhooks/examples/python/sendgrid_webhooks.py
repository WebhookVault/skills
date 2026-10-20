"""Verifies and reads SendGrid Event Webhook requests (signed event webhook). Framework-free: pass the
raw body and the headers; wire it into FastAPI, Flask or anything else as shown in the
webhook-receiver-patterns skill. Python 3.9+ and the cryptography package.

SendGrid signs the timestamp header value followed by the raw body with ECDSA and SHA-256, and sends
the base64 signature in X-Twilio-Email-Event-Webhook-Signature. The verification key is the base64
public key shown in the Event Webhook settings. The body is a JSON array of events.

(The module is not named sendgrid.py so it cannot shadow SendGrid's own package.)
"""

import base64
import binascii
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_der_public_key


def _header(headers, name):
    for key, value in (headers or {}).items():
        if key.lower() == name.lower():
            return value[0] if isinstance(value, list) else value
    return None


def load_public_key(base64_key):
    """Loads the base64 key from the SendGrid settings (DER SubjectPublicKeyInfo). Do this once."""
    if not base64_key:
        raise ValueError("The SendGrid verification key is required (read it from the environment).")
    key = load_der_public_key(base64.b64decode(base64_key))
    if not isinstance(key, ec.EllipticCurvePublicKey):
        raise ValueError("The SendGrid verification key is not an elliptic curve key.")
    return key


def verify(body, headers, public_key):
    """True when the signature over timestamp + raw body verifies with this key."""
    raw = body if isinstance(body, bytes) else (body or "").encode("utf-8")
    signature = _header(headers, "X-Twilio-Email-Event-Webhook-Signature")
    timestamp = _header(headers, "X-Twilio-Email-Event-Webhook-Timestamp")
    if not isinstance(signature, str) or not isinstance(timestamp, str):
        return False
    try:
        der = base64.b64decode(signature, validate=True)
        public_key.verify(der, timestamp.encode("utf-8") + raw, ec.ECDSA(hashes.SHA256()))
        return True
    except (binascii.Error, ValueError, InvalidSignature):
        return False


def handle(body, headers, public_key):
    """Handles one request: verify, then parse the batch.

    Returns the status to answer with and, when accepted, each event's name and sg_event_id (the id
    SendGrid says to deduplicate on). No timestamp window is applied: SendGrid states none and retries
    a failed batch for up to 24 hours, so an age limit could refuse its own retries.
    """
    raw = body if isinstance(body, bytes) else (body or "").encode("utf-8")
    if not verify(raw, headers, public_key):
        return {"status": 401}
    try:
        batch = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {"status": 400}
    if not isinstance(batch, list) or not all(isinstance(e, dict) for e in batch):
        return {"status": 400}

    def text(v):
        return v if isinstance(v, str) else None

    return {"status": 200, "events": [{"type": text(e.get("event")), "id": text(e.get("sg_event_id"))} for e in batch]}
