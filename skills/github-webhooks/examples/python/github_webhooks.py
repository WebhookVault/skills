"""Verifies and reads GitHub webhook deliveries. Framework-free: pass the raw body bytes and the
headers; wire it into FastAPI, Flask or anything else as shown in the webhook-receiver-patterns
skill. Python 3.9+, standard library only.

GitHub signs the raw body with HMAC-SHA256 and the webhook's secret, hex encoded and prefixed
"sha256=", in X-Hub-Signature-256. The older SHA-1 X-Hub-Signature header is never accepted.
There is no timestamp, so a replayed delivery verifies: deduplicate on X-GitHub-Delivery.
Set the webhook's content type to application/json (a form-encoded delivery is not read here).
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
    """True when the request carries a valid GitHub SHA-256 signature over these exact bytes."""
    if not secret:
        raise ValueError("The GitHub webhook secret is required (read it from the environment).")
    raw = body if isinstance(body, bytes) else (body or "").encode("utf-8")
    sig = _header(headers, "X-Hub-Signature-256")
    if not isinstance(sig, str):
        return False
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig.encode("utf-8"), expected.encode("utf-8"))


def handle(body, headers, secret):
    """Handles one request: verify, then parse.

    Returns a dict with the HTTP status to answer with and, when accepted, the event name ("type",
    from X-GitHub-Event), the "action" in the body (None when it has none) and the delivery id to
    deduplicate on ("id", from X-GitHub-Delivery). Answer within ten seconds: queue the work.
    """
    raw = body if isinstance(body, bytes) else (body or "").encode("utf-8")
    if not verify(raw, headers, secret):
        return {"status": 401}

    kind = _header(headers, "X-GitHub-Event")
    if not isinstance(kind, str) or kind == "":
        return {"status": 400}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {"status": 400}
    if not isinstance(payload, dict):
        return {"status": 400}

    delivery = _header(headers, "X-GitHub-Delivery")
    action = payload.get("action")
    return {
        "status": 200,
        "type": kind,
        "action": action if isinstance(action, str) else None,
        "id": delivery if isinstance(delivery, str) and delivery != "" else None,
    }
