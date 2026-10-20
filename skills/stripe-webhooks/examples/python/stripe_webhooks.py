"""Verifies and reads Stripe webhook events. Framework-free: pass the raw body bytes and the headers;
wire it into FastAPI, Flask or anything else as shown in the webhook-receiver-patterns skill.
Python 3.9+, standard library only.

Stripe sends "Stripe-Signature: t=<timestamp>,v1=<hex>[,v1=<hex>...][,v0=<hex>]". Each v1 is
HMAC-SHA256 over "<t>.<raw body>" with the endpoint's signing secret (the whole "whsec_..." string
is the key). While a secret is being rolled there are two v1 values: any one may match. v0 is for
test mode and is never accepted. Stripe's libraries refuse timestamps more than five minutes old.
"""

import hashlib
import hmac
import json
import re
import time

TOLERANCE_SECONDS = 300


def _header(headers, name):
    for key, value in (headers or {}).items():
        if key.lower() == name.lower():
            return value[0] if isinstance(value, list) else value
    return None


def verify(body, headers, secret, now=None, tolerance=TOLERANCE_SECONDS):
    """True when the request carries a valid, fresh Stripe signature over these exact bytes."""
    if not secret:
        raise ValueError("The Stripe endpoint signing secret is required (read it from the environment).")
    raw = body if isinstance(body, bytes) else (body or "").encode("utf-8")
    value = _header(headers, "Stripe-Signature")
    if not isinstance(value, str):
        return False

    timestamps = []
    candidates = []
    for part in value.split(","):
        key, sep, val = part.partition("=")
        if not sep:
            continue
        if key == "t":
            timestamps.append(val)
        elif key == "v1":  # v0 and unknown keys are ignored
            candidates.append(val)
    if len(timestamps) != 1 or not re.fullmatch(r"[0-9]{1,12}", timestamps[0]) or not candidates:
        return False
    ts = timestamps[0]
    now = int(time.time()) if now is None else now
    if abs(now - int(ts)) > tolerance:
        return False

    mac = hmac.new(secret.encode("utf-8"), ts.encode() + b"." + raw, hashlib.sha256).hexdigest().encode("utf-8")
    # Check every candidate (no early exit) so the time taken does not say which one matched.
    ok = False
    for candidate in candidates:
        ok = hmac.compare_digest(candidate.encode("utf-8"), mac) or ok
    return ok


def handle(body, headers, secret, now=None, tolerance=TOLERANCE_SECONDS):
    """Handles one request: verify, then parse.

    Returns a dict with the HTTP status to answer with and, when accepted, the event name ("type")
    and the event id to deduplicate on ("id"). Answer 2xx quickly: queue the work.
    """
    raw = body if isinstance(body, bytes) else (body or "").encode("utf-8")
    if not verify(raw, headers, secret, now, tolerance):
        return {"status": 401}

    try:
        event = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {"status": 400}
    if not isinstance(event, dict):
        return {"status": 400}
    if not isinstance(event.get("id"), str) or not isinstance(event.get("type"), str):
        return {"status": 400}
    return {"status": 200, "type": event["type"], "id": event["id"]}
