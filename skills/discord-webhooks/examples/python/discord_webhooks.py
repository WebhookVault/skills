"""Verifies and reads Discord Webhook Events and Interactions endpoint requests. Framework-free: pass
the raw body bytes and the headers; wire it into FastAPI, Flask or anything else as shown in the
webhook-receiver-patterns skill. Python 3.9+; needs the cryptography package (see requirements.txt).

Both use the same signature: Ed25519 over "<X-Signature-Timestamp><raw body>", hex encoded in
X-Signature-Ed25519, checked with the application's public key (64 hex characters, from the
developer portal). Discord sends no tolerance guidance for it and neither does this code: the
timestamp is part of the signed message, nothing more. Discord also sends requests with a bad
signature on purpose when you save the endpoint URL and expects 401 for them.

handle_event is for Webhook Events (answer 204); handle_interaction is for the Interactions endpoint
(answer 200 with a JSON body). Use the one that matches the URL you registered.
"""

import json
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

_HEX_SIGNATURE = re.compile(r"[0-9a-fA-F]{128}")
_HEX_KEY = re.compile(r"[0-9a-fA-F]{64}")


def _header(headers, name):
    for key, value in (headers or {}).items():
        if key.lower() == name.lower():
            return value[0] if isinstance(value, list) else value
    return None


def verify(body, headers, public_key):
    """True when the request carries a valid Discord Ed25519 signature over these exact bytes."""
    if not public_key:
        raise ValueError("The Discord application public key is required (read it from the environment).")
    raw = body if isinstance(body, bytes) else (body or "").encode("utf-8")
    ts = _header(headers, "X-Signature-Timestamp")
    sig = _header(headers, "X-Signature-Ed25519")
    if not isinstance(ts, str) or not ts or not isinstance(sig, str):
        return False
    if not _HEX_SIGNATURE.fullmatch(sig) or not _HEX_KEY.fullmatch(public_key):
        return False
    try:
        key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key))
        key.verify(bytes.fromhex(sig), ts.encode("utf-8") + raw)
        return True
    except (InvalidSignature, ValueError):
        return False


def _parse_object(raw):
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def handle_event(body, headers, public_key):
    """Webhook Events: verify, then parse.

    A PING (outer type 0) answers 204 with type "PING"; an event (outer type 1) answers 204 with
    "type" = event.type, e.g. APPLICATION_AUTHORIZED. Discord does not document an event id, so
    there is nothing to deduplicate on in the envelope.
    """
    raw = body if isinstance(body, bytes) else (body or "").encode("utf-8")
    if not verify(raw, headers, public_key):
        return {"status": 401}
    payload = _parse_object(raw)
    if payload is None:
        return {"status": 400}
    outer = payload.get("type")
    if outer == 0 and not isinstance(outer, bool):
        return {"status": 204, "type": "PING"}
    if outer == 1 and not isinstance(outer, bool):
        event = payload.get("event")
        event_type = event.get("type") if isinstance(event, dict) else None
        if isinstance(event_type, str):
            return {"status": 204, "type": event_type}
    return {"status": 400}


def handle_interaction(body, headers, public_key):
    """Interactions endpoint: verify, then parse.

    "type" is the integer interaction type and "id" the interaction id. For a PING (type 1) "reply"
    is the exact body to answer with, {"type":1}; for anything else it is None and you answer with a
    real interaction response within three seconds.
    """
    raw = body if isinstance(body, bytes) else (body or "").encode("utf-8")
    if not verify(raw, headers, public_key):
        return {"status": 401}
    payload = _parse_object(raw)
    if payload is None:
        return {"status": 400}
    kind, interaction_id = payload.get("type"), payload.get("id")
    if not isinstance(kind, int) or isinstance(kind, bool) or not isinstance(interaction_id, str):
        return {"status": 400}
    return {"status": 200, "type": kind, "id": interaction_id, "reply": '{"type":1}' if kind == 1 else None}
