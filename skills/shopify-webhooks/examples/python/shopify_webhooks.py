"""Verifies and reads Shopify webhooks. Framework-free: pass the raw body bytes and the headers; wire
it into FastAPI, Flask or anything else as shown in the webhook-receiver-patterns skill.
Python 3.9+, standard library only.

Shopify signs the raw body with HMAC-SHA256 and the app's client secret, base64 encoded (not hex),
in X-Shopify-Hmac-Sha256. There is no timestamp. X-Shopify-Webhook-Id is the same on every
delivery attempt of one webhook, X-Shopify-Event-Id is shared by all webhooks for one event:
deduplicate on the first, or on the second to collapse subscriptions to the same event.
"""

import base64
import hashlib
import hmac
import json


def _header(headers, name):
    for key, value in (headers or {}).items():
        if key.lower() == name.lower():
            return value[0] if isinstance(value, list) else value
    return None


def _text(value):
    return value if isinstance(value, str) and value != "" else None


def verify(body, headers, secret):
    """True when the request carries a valid Shopify signature over these exact bytes."""
    if not secret:
        raise ValueError("The Shopify client secret is required (read it from the environment).")
    raw = body if isinstance(body, bytes) else (body or "").encode("utf-8")
    sig = _header(headers, "X-Shopify-Hmac-Sha256")
    if not isinstance(sig, str):
        return False
    digest = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).digest()
    return hmac.compare_digest(sig.encode("utf-8"), base64.b64encode(digest))


def handle(body, headers, secret):
    """Handles one request: verify, then parse.

    Returns a dict with the HTTP status to answer with and, when accepted, the topic ("type"), the
    webhook id to deduplicate on ("id"), the event id ("eventId") and the shop's domain ("shop").
    Answer within five seconds: queue the work.
    """
    raw = body if isinstance(body, bytes) else (body or "").encode("utf-8")
    if not verify(raw, headers, secret):
        return {"status": 401}

    kind = _text(_header(headers, "X-Shopify-Topic"))
    webhook_id = _text(_header(headers, "X-Shopify-Webhook-Id"))
    if kind is None or webhook_id is None:
        return {"status": 400}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {"status": 400}
    if not isinstance(payload, dict):
        return {"status": 400}

    return {
        "status": 200,
        "type": kind,
        "id": webhook_id,
        "eventId": _text(_header(headers, "X-Shopify-Event-Id")),
        "shop": _text(_header(headers, "X-Shopify-Shop-Domain")),
    }
