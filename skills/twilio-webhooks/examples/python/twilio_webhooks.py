"""Verifies and reads Twilio webhook requests (form-encoded and JSON). Framework-free: pass the raw
body, the headers and the public URL Twilio called; wire it into FastAPI, Flask or anything else as
shown in the webhook-receiver-patterns skill. Python 3.9+, standard library only.

Twilio signs with HMAC-SHA1 and the account auth token, base64 encoded, in X-Twilio-Signature.
Form bodies: the full URL followed by every POST parameter name and value, sorted by name.
JSON bodies: the URL carries bodySHA256 (hex SHA-256 of the raw body) and nothing is appended.
The URL must be the one Twilio called, exactly: scheme, host, port, path, query and encoding.

(The module is not named twilio.py so it cannot shadow Twilio's own package.)
"""

import base64
import hashlib
import hmac
import json
from urllib.parse import parse_qs, parse_qsl, urlsplit


def _header(headers, name):
    for key, value in (headers or {}).items():
        if key.lower() == name.lower():
            return value[0] if isinstance(value, list) else value
    return None


def _is_json(headers):
    return str(_header(headers, "Content-Type") or "").lower().startswith("application/json")


def form_fields(raw):
    """The form fields as Twilio sent them, in order ("+" is a space, then percent-decoding)."""
    return parse_qsl(raw.decode("utf-8"), keep_blank_values=True)


def verify(body, headers, url, auth_token):
    """True when X-Twilio-Signature matches this URL and body."""
    if not auth_token:
        raise ValueError("The Twilio auth token is required (read it from the environment).")
    raw = body if isinstance(body, bytes) else (body or "").encode("utf-8")
    signature = _header(headers, "X-Twilio-Signature")
    if not isinstance(signature, str) or not isinstance(url, str):
        return False

    signed = url
    if _is_json(headers):
        claimed = parse_qs(urlsplit(url).query).get("bodySHA256", [None])[0]
        if not claimed:
            return False
        actual = hashlib.sha256(raw).hexdigest()
        if not hmac.compare_digest(claimed.lower().encode(), actual.encode()):
            return False
    else:
        try:
            fields = form_fields(raw)
        except UnicodeDecodeError:
            return False
        # Sorted by name in code-point order (Twilio: "Unix-style case-sensitive"); sorted() is stable,
        # so repeated names keep the order they arrived in.
        for name, value in sorted(fields, key=lambda kv: kv[0]):
            signed += name + value
    expected = base64.b64encode(hmac.new(auth_token.encode("utf-8"), signed.encode("utf-8"), hashlib.sha1).digest()).decode()
    return hmac.compare_digest(signature.encode("utf-8"), expected.encode("utf-8"))


def handle(body, headers, url, auth_token):
    """Handles one request: verify, then read.

    Returns the status to answer with and, when accepted, the status value Twilio reported ("type")
    and the resource SID ("id"). Twilio has no event id; a retry carries I-Twilio-Idempotency-Token,
    which is the better key when present.
    """
    raw = body if isinstance(body, bytes) else (body or "").encode("utf-8")
    if not verify(raw, headers, url, auth_token):
        return {"status": 401}
    if _is_json(headers):
        try:
            fields = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {"status": 400}
        if not isinstance(fields, dict):
            return {"status": 400}
    else:
        fields = dict(form_fields(raw))

    def pick(*names):
        return next((fields[n] for n in names if isinstance(fields.get(n), str) and fields[n]), None)

    return {
        "status": 200,
        "type": pick("MessageStatus", "SmsStatus", "CallStatus"),
        "id": pick("MessageSid", "SmsSid", "CallSid"),
        "idempotencyToken": _header(headers, "I-Twilio-Idempotency-Token"),
    }
