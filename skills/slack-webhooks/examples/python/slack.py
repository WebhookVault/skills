"""Verifies and reads Slack Events API and interactivity requests. Framework-free: pass the raw body
bytes and the headers; wire it into FastAPI, Flask or anything else as shown in the
webhook-receiver-patterns skill. Python 3.9+, standard library only.

Slack signs "v0:<X-Slack-Request-Timestamp>:<raw body>" with HMAC-SHA256 and the app's signing
secret, hex encoded and prefixed "v0=", in X-Slack-Signature. Slack's own example rejects a
timestamp more than five minutes from local time.
"""

import hashlib
import hmac
import json
import re
import time
from urllib.parse import parse_qs

TOLERANCE_SECONDS = 300


def _header(headers, name):
    for key, value in (headers or {}).items():
        if key.lower() == name.lower():
            return value[0] if isinstance(value, list) else value
    return None


def verify(body, headers, secret, now=None, tolerance=TOLERANCE_SECONDS):
    """True when the request carries a valid, fresh Slack signature over these exact bytes."""
    if not secret:
        raise ValueError("The Slack signing secret is required (read it from the environment).")
    raw = body if isinstance(body, bytes) else (body or "").encode("utf-8")
    ts = _header(headers, "X-Slack-Request-Timestamp")
    sig = _header(headers, "X-Slack-Signature")
    if not isinstance(ts, str) or not re.fullmatch(r"\d{1,12}", ts) or not isinstance(sig, str):
        return False
    now = int(time.time()) if now is None else now
    if abs(now - int(ts)) > tolerance:
        return False
    mac = hmac.new(secret.encode("utf-8"), b"v0:" + ts.encode() + b":" + raw, hashlib.sha256)
    return hmac.compare_digest(sig.encode("utf-8"), ("v0=" + mac.hexdigest()).encode("utf-8"))


def handle(body, headers, secret, now=None):
    """Handles one request: verify, then parse.

    Returns a dict with the HTTP status to answer with and, when accepted, the event name ("type"),
    the id to deduplicate on ("id", Slack's event_id; None for interactions, which have none) and,
    for url_verification, the text to reply with. Answer within three seconds: queue the work.
    """
    raw = body if isinstance(body, bytes) else (body or "").encode("utf-8")
    if not verify(raw, headers, secret, now):
        return {"status": 401}

    content_type = str(_header(headers, "Content-Type") or "").lower()
    try:
        if content_type.startswith("application/x-www-form-urlencoded"):
            # Interactivity: one form field, "payload", holding JSON.
            field = parse_qs(raw.decode("utf-8"), keep_blank_values=True).get("payload")
            if not field:
                return {"status": 400}
            payload = json.loads(field[0])
        else:
            payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {"status": 400}
    if not isinstance(payload, dict):
        return {"status": 400}

    kind = payload.get("type")
    if kind == "url_verification":
        # Answered only after the signature checked out, so nobody else can register this URL.
        challenge = payload.get("challenge")
        if not isinstance(challenge, str):
            return {"status": 400}
        return {"status": 200, "type": "url_verification", "id": None, "reply": challenge}
    if kind == "event_callback":
        event = payload.get("event")
        event_type = event.get("type") if isinstance(event, dict) else None
        event_id = payload.get("event_id")
        if not isinstance(event_type, str) or not isinstance(event_id, str):
            return {"status": 400}
        return {"status": 200, "type": event_type, "id": event_id}
    if not isinstance(kind, str):
        return {"status": 400}
    return {"status": 200, "type": kind, "id": None}
