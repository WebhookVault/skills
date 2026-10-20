"""Verifies and reads Lemon Squeezy webhooks. Framework-free: pass the raw body bytes and the
headers; wire it into FastAPI, Flask or anything else as shown in the webhook-receiver-patterns
skill. Python 3.9+, standard library only.

Lemon Squeezy signs the raw body with HMAC-SHA256 and the webhook's signing secret, hex encoded,
in X-Signature. There is no timestamp and no event or delivery id. The event name is read from
the signed body (meta.event_name); the unsigned X-Event-Name header is only cross-checked.
"""

import hashlib
import hmac
import json


def _header(headers, name):
    for key, value in (headers or {}).items():
        if key.lower() == name.lower():
            return value[0] if isinstance(value, list) else value
    return None


def verify(body, headers, secret):
    """True when the request carries a valid Lemon Squeezy signature over these exact bytes."""
    if not secret:
        raise ValueError("The Lemon Squeezy signing secret is required (read it from the environment).")
    raw = body if isinstance(body, bytes) else (body or "").encode("utf-8")
    sig = _header(headers, "X-Signature")
    if not isinstance(sig, str):
        return False
    expected = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig.encode("utf-8"), expected.encode("utf-8"))


def handle(body, headers, secret):
    """Handles one request: verify, then parse.

    Returns a dict with the HTTP status to answer with and, when accepted, the event name ("type"),
    "id" (always None: Lemon Squeezy sends no id to deduplicate on: a hash of the body catches a
    resent request, and applying only newer state per "resource" covers the rest) and "resource"
    ("<data.type>/<data.id>", None when either is missing).
    """
    raw = body if isinstance(body, bytes) else (body or "").encode("utf-8")
    if not verify(raw, headers, secret):
        return {"status": 401}

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {"status": 400}
    if not isinstance(payload, dict):
        return {"status": 400}

    meta = payload.get("meta")
    kind = meta.get("event_name") if isinstance(meta, dict) else None
    if not isinstance(kind, str) or kind == "":
        return {"status": 400}
    claimed = _header(headers, "X-Event-Name")
    if claimed is not None and claimed != kind:
        return {"status": 400}

    data = payload.get("data")
    data = data if isinstance(data, dict) else {}
    data_type, data_id = data.get("type"), data.get("id")
    ok = isinstance(data_type, str) and data_type != "" and isinstance(data_id, str) and data_id != ""
    return {"status": 200, "type": kind, "id": None, "resource": f"{data_type}/{data_id}" if ok else None}
