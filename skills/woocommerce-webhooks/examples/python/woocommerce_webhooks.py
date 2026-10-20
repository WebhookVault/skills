"""Verifies and reads WooCommerce webhooks. Framework-free: pass the raw body bytes and the headers;
wire it into FastAPI, Flask or anything else as shown in the webhook-receiver-patterns skill.
Python 3.9+, standard library only.

WooCommerce signs the raw body with HMAC-SHA256 and the webhook's secret, base64 encoded, in
X-WC-Webhook-Signature. There is no timestamp. When a webhook is saved WooCommerce sends one
unsigned ping whose body is exactly "webhook_id=<number>"; that single shape is acknowledged and
nothing else unsigned is.
"""

import base64
import hashlib
import hmac
import json
import re


def _header(headers, name):
    for key, value in (headers or {}).items():
        if key.lower() == name.lower():
            return value[0] if isinstance(value, list) else value
    return None


def verify(body, headers, secret):
    """True when the request carries a valid WooCommerce signature over these exact bytes."""
    if not secret:
        raise ValueError("The WooCommerce webhook secret is required (read it from the environment).")
    raw = body if isinstance(body, bytes) else (body or "").encode("utf-8")
    sig = _header(headers, "X-WC-Webhook-Signature")
    if not isinstance(sig, str):
        return False
    digest = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).digest()
    return hmac.compare_digest(sig.encode("utf-8"), base64.b64encode(digest))


def handle(body, headers, secret):
    """Handles one request: verify, then parse.

    Returns a dict with the HTTP status to answer with and, when accepted, the topic ("type", for
    example "order.created") and the delivery id to deduplicate on ("id", None when WooCommerce sent
    none). The activation ping answers 200 with type "ping" and id None. Answer quickly: queue the work.
    """
    raw = body if isinstance(body, bytes) else (body or "").encode("utf-8")

    # Only a request with no signature header at all AND exactly this body is the ping.
    # fullmatch, because "$" would also accept a trailing newline.
    if _header(headers, "X-WC-Webhook-Signature") is None and re.fullmatch(rb"webhook_id=[0-9]+", raw):
        if not secret:
            raise ValueError("The WooCommerce webhook secret is required (read it from the environment).")
        return {"status": 200, "type": "ping", "id": None}
    if not verify(raw, headers, secret):
        return {"status": 401}

    kind = _header(headers, "X-WC-Webhook-Topic")
    if not isinstance(kind, str) or kind == "":
        return {"status": 400}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {"status": 400}
    if not isinstance(payload, dict):
        return {"status": 400}

    delivery = _header(headers, "X-WC-Webhook-Delivery-ID")
    return {"status": 200, "type": kind, "id": delivery if isinstance(delivery, str) and delivery != "" else None}
