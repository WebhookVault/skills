"""Webhook signature verification for the common scheme families. Python 3.9 or later.

The HMAC families use only the standard library. Ed25519 and ECDSA need the `cryptography` package
(see requirements.txt). Every function takes the RAW body as bytes, exactly as received, never a
parsed object, and returns True or False without raising.

`now` is the current Unix time in seconds; it defaults to the real clock and is a parameter so tests
are deterministic. `tolerance` is how old (or how far in the future) a signed timestamp may be.
"""

import base64
import binascii
import hashlib
import hmac
import re
import time

_SECONDS = re.compile(r"^\d{1,12}$")
_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
_HEX128 = re.compile(r"^[0-9a-fA-F]{128}$")


def _now():
    return int(time.time())


def safe_equal(a, b):
    """Constant-time comparison of two strings; False when either is missing."""
    if not isinstance(a, str) or not isinstance(b, str):
        return False
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def is_fresh(timestamp, now=None, tolerance=300):
    """True when `timestamp` is whole Unix seconds within `tolerance` of `now`."""
    if not isinstance(timestamp, str) or not _SECONDS.match(timestamp):
        return False
    return abs((_now() if now is None else now) - int(timestamp)) <= tolerance


def _mac(algorithm, key, *parts):
    mac = hmac.new(key if isinstance(key, bytes) else key.encode("utf-8"), digestmod=algorithm)
    for part in parts:
        mac.update(part)
    return mac.digest()


def verify_hmac_body(body, signature, secret, encoding="hex", prefix="", algorithm=hashlib.sha256):
    """HMAC over the raw body; `encoding` "hex" or "base64"; `prefix` such as "sha256="."""
    if not secret or not isinstance(signature, str):
        return False
    digest = _mac(algorithm, secret, body)
    expected = prefix + (digest.hex() if encoding == "hex" else base64.b64encode(digest).decode())
    return safe_equal(signature, expected)


def verify_timestamp_header(body, header, secret, now=None, tolerance=300,
                            pair_separator=",", timestamp_key="t", signature_key="v1", joiner="."):
    """A timestamp and one or more signatures in one header, such as "t=1,v1=abc" over "<t>.<body>"
    or "ts=1;h1=abc" over "<ts>:<body>". Any one signature entry matching is enough (rotation)."""
    if not secret or not isinstance(header, str):
        return False
    pairs = []
    for part in header.split(pair_separator):
        key, _, value = part.partition("=")
        pairs.append((key.strip(), value.strip()))
    stamps = [v for k, v in pairs if k == timestamp_key]
    if len(stamps) != 1 or not is_fresh(stamps[0], now, tolerance):
        return False
    expected = _mac(hashlib.sha256, secret, (stamps[0] + joiner).encode("utf-8"), body).hex()
    return any(k == signature_key and safe_equal(v, expected) for k, v in pairs)


def verify_versioned_timestamp(body, timestamp, signature, secret, now=None, tolerance=300, version="v0"):
    """A timestamp in its own header and "v0=<hex>" over "v0:<timestamp>:<body>"."""
    if not secret or not is_fresh(timestamp, now, tolerance):
        return False
    digest = _mac(hashlib.sha256, secret, f"{version}:{timestamp}:".encode("utf-8"), body)
    return safe_equal(signature, f"{version}=" + digest.hex())


def verify_standard_webhooks(body, msg_id, timestamp, signature, secret, now=None, tolerance=300):
    """Standard Webhooks: "whsec_" plus base64 key; "<id>.<timestamp>.<body>"; "v1,<base64>" entries."""
    if not isinstance(secret, str) or not secret.startswith("whsec_") or not msg_id or not isinstance(signature, str):
        return False
    if not is_fresh(timestamp, now, tolerance):
        return False
    try:
        key = base64.b64decode(secret[len("whsec_"):], validate=True)
    except (binascii.Error, ValueError):
        return False
    if not key:
        return False
    expected = base64.b64encode(_mac(hashlib.sha256, key, f"{msg_id}.{timestamp}.".encode("utf-8"), body)).decode()
    for entry in signature.split(" "):
        version, _, value = entry.partition(",")
        if version == "v1" and safe_equal(value, expected):
            return True
    return False


def verify_url_form(url, params, signature, secret):
    """HMAC-SHA1 over the full URL the sender called plus form fields sorted by name, base64.
    `url` comes from your configuration, never from the incoming request."""
    if not secret or not isinstance(url, str) or not isinstance(signature, str):
        return False
    data = url + "".join(name + str(params[name]) for name in sorted(params or {}))
    expected = base64.b64encode(_mac(hashlib.sha1, secret, data.encode("utf-8"))).decode()
    return safe_equal(signature, expected)


def verify_ed25519(body, timestamp, signature, public_key, now=None, tolerance=300):
    """Ed25519 over "<timestamp><body>"; hex signature; the public key as 64 hex characters."""
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    if not isinstance(public_key, str) or not _HEX64.match(public_key):
        return False
    if not isinstance(signature, str) or not _HEX128.match(signature) or not is_fresh(timestamp, now, tolerance):
        return False
    try:
        key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key))
        key.verify(bytes.fromhex(signature), timestamp.encode("utf-8") + body)
        return True
    except (InvalidSignature, ValueError):
        return False


def verify_ecdsa_p256(body, timestamp, signature, public_key, now=None, tolerance=300):
    """ECDSA P-256 with SHA-256 over "<timestamp><body>"; base64 DER signature; base64 SPKI key."""
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.serialization import load_der_public_key

    if not isinstance(public_key, str) or not isinstance(signature, str) or not is_fresh(timestamp, now, tolerance):
        return False
    try:
        key = load_der_public_key(base64.b64decode(public_key, validate=True))
        if not isinstance(key, ec.EllipticCurvePublicKey) or key.curve.name != "secp256r1":
            return False
        key.verify(base64.b64decode(signature, validate=True), timestamp.encode("utf-8") + body, ec.ECDSA(hashes.SHA256()))
        return True
    except (InvalidSignature, ValueError, binascii.Error):
        return False


def verify_shared_token(value, token):
    """A shared token sent in a header (no signature), compared in constant time."""
    return bool(token) and safe_equal(value, token)
