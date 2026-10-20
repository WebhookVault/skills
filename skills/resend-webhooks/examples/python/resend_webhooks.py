"""Verifies and reads Resend webhooks. Framework-free: pass the raw body bytes and the headers; wire it
into FastAPI, Flask or anything else as shown in the webhook-receiver-patterns skill.
Python 3.9+, standard library only.

Resend delivers through Svix, which follows the Standard Webhooks scheme. The signing key is the
base64 text after "whsec_" in the signing secret. The signed string is
"<svix-id>.<svix-timestamp>.<raw body>"; HMAC-SHA256 with the decoded key, base64 encoded, goes in
svix-signature as space-separated "v1,<signature>" entries (several while a secret is rotated).
Svix's libraries reject a timestamp more than five minutes from local time.
"""

import base64
import binascii
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


def _signing_key(secret):
    encoded = secret[len("whsec_"):] if secret.startswith("whsec_") else secret
    try:
        key = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        key = b""
    if not key:
        raise ValueError("The Resend signing secret is not valid base64 after the whsec_ prefix.")
    return key


def verify(body, headers, secret, now=None, tolerance=TOLERANCE_SECONDS):
    """True when the request carries a valid, fresh Resend signature over these exact bytes."""
    if not secret:
        raise ValueError("The Resend signing secret is required (read it from the environment).")
    key = _signing_key(secret)
    raw = body if isinstance(body, bytes) else (body or "").encode("utf-8")
    msg_id = _header(headers, "svix-id")
    ts = _header(headers, "svix-timestamp")
    sigs = _header(headers, "svix-signature")
    if not isinstance(msg_id, str) or not msg_id or not isinstance(sigs, str):
        return False
    if not isinstance(ts, str) or not re.fullmatch(r"\d{1,12}", ts):
        return False
    now = int(time.time()) if now is None else now
    if abs(now - int(ts)) > tolerance:
        return False

    mac = hmac.new(key, f"{msg_id}.{ts}.".encode("utf-8") + raw, hashlib.sha256)
    expected = base64.b64encode(mac.digest())
    # Only v1 entries count; other versions are ignored. Check every candidate, no early exit.
    ok = False
    for entry in sigs.split():
        version, sep, signature = entry.partition(",")
        if sep and version == "v1":
            ok = hmac.compare_digest(signature.encode("utf-8"), expected) or ok
    return ok


def handle(body, headers, secret, now=None):
    """Handles one request: verify, then parse.

    Returns a dict with the HTTP status to answer with and, when accepted, the event name ("type")
    and the id to deduplicate on ("id", the svix-id header, which stays the same across retries).
    Answer 2xx quickly and process elsewhere.
    """
    raw = body if isinstance(body, bytes) else (body or "").encode("utf-8")
    if not verify(raw, headers, secret, now):
        return {"status": 401}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {"status": 400}
    if not isinstance(payload, dict) or not isinstance(payload.get("type"), str):
        return {"status": 400}
    return {"status": 200, "type": payload["type"], "id": _header(headers, "svix-id")}
