"""Verifies and reads Paddle Billing notifications. Framework-free: pass the raw body bytes and the
headers; wire it into FastAPI, Flask or anything else as shown in the webhook-receiver-patterns
skill. Python 3.9+, standard library only.

Paddle sends "Paddle-Signature: ts=<unix seconds>;h1=<hex>" (several h1 values while a secret is
being rotated). Each h1 is HMAC-SHA256, keyed with the notification destination's secret key string,
over "<ts>:<raw body>". Paddle's guidance is to reject a timestamp more than five seconds from
local time, which is tight: keep the server clock synchronised.
"""

import hashlib
import hmac
import json
import re
import time

TOLERANCE_SECONDS = 5


def _header(headers, name):
    for key, value in (headers or {}).items():
        if key.lower() == name.lower():
            return value[0] if isinstance(value, list) else value
    return None


def verify(body, headers, secret, now=None, tolerance=TOLERANCE_SECONDS):
    """True when the request carries a valid, fresh Paddle signature over these exact bytes."""
    if not secret:
        raise ValueError("The Paddle notification secret key is required (read it from the environment).")
    raw = body if isinstance(body, bytes) else (body or "").encode("utf-8")
    value = _header(headers, "Paddle-Signature")
    if not isinstance(value, str):
        return False

    timestamps, signatures = [], []
    for part in value.split(";"):
        key, sep, val = part.partition("=")
        if not sep:
            continue
        key, val = key.strip(), val.strip()
        if key == "ts":
            timestamps.append(val)
        elif key == "h1":
            signatures.append(val)
    if len(timestamps) != 1 or not re.fullmatch(r"\d{1,12}", timestamps[0]) or not signatures:
        return False
    ts = timestamps[0]
    now = int(time.time()) if now is None else now
    if abs(now - int(ts)) > tolerance:
        return False

    expected = hmac.new(secret.encode("utf-8"), ts.encode() + b":" + raw, hashlib.sha256).hexdigest().encode()
    # Check every candidate (no early exit on the first match) so timing does not reveal which matched.
    ok = False
    for sig in signatures:
        ok = hmac.compare_digest(sig.lower().encode("utf-8"), expected) or ok
    return ok


def handle(body, headers, secret, now=None):
    """Handles one request: verify, then parse.

    Returns a dict with the HTTP status to answer with and, when accepted, the event name ("type",
    Paddle's event_type) and the id to deduplicate on ("id", Paddle's event_id). Answer 200 quickly
    and process elsewhere: Paddle retries on anything else.
    """
    raw = body if isinstance(body, bytes) else (body or "").encode("utf-8")
    if not verify(raw, headers, secret, now):
        return {"status": 401}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {"status": 400}
    if not isinstance(payload, dict):
        return {"status": 400}
    event_type, event_id = payload.get("event_type"), payload.get("event_id")
    if not isinstance(event_type, str) or not isinstance(event_id, str):
        return {"status": 400}
    return {"status": 200, "type": event_type, "id": event_id}
