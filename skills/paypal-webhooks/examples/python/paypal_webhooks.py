"""Verifies and reads PayPal webhooks. Framework-free: pass the raw body bytes and the headers; wire it
into FastAPI, Flask or anything else as shown in the webhook-receiver-patterns skill.
Python 3.9+; needs the cryptography package (see requirements.txt) for the certificate and RSA.

PayPal signs "<PAYPAL-TRANSMISSION-ID>|<PAYPAL-TRANSMISSION-TIME>|<webhook id>|<crc32>", where crc32
is the CRC-32 (IEEE, as zlib) of the raw body as an unsigned decimal number. The signature is RSA
PKCS#1 v1.5 with SHA-256, base64 encoded, in PAYPAL-TRANSMISSION-SIG, and PAYPAL-AUTH-ALGO must be
SHA256withRSA. The public key is the certificate at PAYPAL-CERT-URL, so that header is attacker
controlled until proven otherwise: a certificate fetched from anywhere else would let anyone sign.
PayPal's docs do not state a host rule, so this one is ours: the URL must be https, on paypal.com or a
subdomain of it, with no userinfo and no non-default port. Only a URL that passes is ever fetched.

Pass fetch_certificate(url), which returns the certificate as PEM text. Cache the certificates by URL:
they change rarely, and fetching on every webhook adds latency and a failure mode. A fetch that raises
gives 500 so PayPal retries; it is not a verdict on the signature.
"""

import base64
import binascii
import json
import re
import zlib
from urllib.parse import urlsplit

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa


class CertificateFetchError(Exception):
    """The certificate could not be fetched (not a verdict on the signature)."""


def _header(headers, name):
    for key, value in (headers or {}).items():
        if key.lower() == name.lower():
            return value[0] if isinstance(value, list) else value
    return None


def is_trusted_certificate_url(value):
    """True only for an https URL on paypal.com or a subdomain, with no userinfo and the default port."""
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError:
        return False
    if parts.scheme != "https" or "@" in parts.netloc or port not in (None, 443):
        return False
    host = parts.hostname or ""
    if not re.fullmatch(r"[a-z0-9.-]+", host):
        return False
    return host == "paypal.com" or host.endswith(".paypal.com")


def _require(webhook_id, fetch_certificate):
    if not webhook_id:
        raise ValueError("The PayPal webhook id is required (read it from the environment).")
    if not callable(fetch_certificate):
        raise ValueError("fetch_certificate(url) is required.")


def verify(body, headers, *, webhook_id, fetch_certificate):
    """True when the request carries a valid PayPal signature over these exact bytes.

    Raises CertificateFetchError when the certificate could not be fetched.
    """
    _require(webhook_id, fetch_certificate)
    raw = body if isinstance(body, bytes) else (body or "").encode("utf-8")
    transmission_id = _header(headers, "PAYPAL-TRANSMISSION-ID")
    transmission_time = _header(headers, "PAYPAL-TRANSMISSION-TIME")
    sig = _header(headers, "PAYPAL-TRANSMISSION-SIG")
    cert_url = _header(headers, "PAYPAL-CERT-URL")
    algo = _header(headers, "PAYPAL-AUTH-ALGO")
    if not all(isinstance(v, str) and v for v in (transmission_id, transmission_time, sig, cert_url)):
        return False
    if algo != "SHA256withRSA":
        return False
    if not is_trusted_certificate_url(cert_url):
        return False

    try:
        pem = fetch_certificate(cert_url)
    except Exception as err:
        raise CertificateFetchError(f"Could not fetch the PayPal certificate: {err}") from err

    try:
        key = x509.load_pem_x509_certificate(pem.encode("utf-8")).public_key()
        if not isinstance(key, rsa.RSAPublicKey):
            return False
        signature = base64.b64decode(sig, validate=True)
        signed = f"{transmission_id}|{transmission_time}|{webhook_id}|{zlib.crc32(raw) & 0xFFFFFFFF}".encode("utf-8")
        key.verify(signature, signed, padding.PKCS1v15(), hashes.SHA256())
        return True
    except (InvalidSignature, ValueError, binascii.Error):
        return False  # bad signature encoding, not a certificate, or the signature does not match


def handle(body, headers, *, webhook_id, fetch_certificate):
    """Handles one request: verify, then parse.

    Returns a dict with the HTTP status to answer with and, when accepted, the event name ("type",
    event_type) and the id to deduplicate on ("id", the body's id). 500 means the certificate could
    not be fetched: PayPal will retry.
    """
    _require(webhook_id, fetch_certificate)
    raw = body if isinstance(body, bytes) else (body or "").encode("utf-8")
    try:
        valid = verify(raw, headers, webhook_id=webhook_id, fetch_certificate=fetch_certificate)
    except CertificateFetchError:
        return {"status": 500}
    if not valid:
        return {"status": 401}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {"status": 400}
    if not isinstance(payload, dict):
        return {"status": 400}
    event_type, event_id = payload.get("event_type"), payload.get("id")
    if not isinstance(event_type, str) or not isinstance(event_id, str):
        return {"status": 400}
    return {"status": 200, "type": event_type, "id": event_id}
