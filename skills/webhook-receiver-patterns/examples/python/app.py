"""A webhook receiver skeleton for FastAPI: cap the size, read the raw bytes, verify the signature,
parse, deduplicate on the event id, acknowledge, and hand the work to a queue.

The signature scheme here is a common one: header "Webhook-Signature: t=<unix>,v1=<hex>" with
HMAC-SHA256 over "<t>.<raw body>". Swap verify() for your sender's scheme (see the
webhook-signature-verification skill). The store and queue are in memory for the example; in
production the store is a database table with a unique key and the queue is a real queue.

    WEBHOOK_SECRET=<test secret> uvicorn app:app
"""

import hashlib
import hmac
import json
import os
import re
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

MAX_BODY_BYTES = 256 * 1024
TOLERANCE_SECONDS = 300
_SECONDS = re.compile(r"^\d{1,12}$")


def verify(raw: bytes, header, secret: str, now=None) -> bool:
    if not isinstance(header, str) or not secret:
        return False
    pairs = [part.partition("=") for part in header.split(",")]
    pairs = [(k.strip(), v.strip()) for k, _, v in pairs]
    stamps = [v for k, v in pairs if k == "t"]
    if len(stamps) != 1 or not _SECONDS.match(stamps[0]):
        return False
    if abs((int(time.time()) if now is None else now) - int(stamps[0])) > TOLERANCE_SECONDS:
        return False
    expected = hmac.new(secret.encode(), stamps[0].encode() + b"." + raw, hashlib.sha256).hexdigest()
    return any(k == "v1" and hmac.compare_digest(v.encode(), expected.encode()) for k, v in pairs)


class MemoryStore:
    """Remembers event ids. first_time(id) is True only the first time an id is seen."""

    def __init__(self):
        self._seen = set()

    async def first_time(self, event_id: str) -> bool:
        if event_id in self._seen:
            return False
        self._seen.add(event_id)
        return True


async def read_capped(request: Request):
    """The raw body, or None when it is larger than MAX_BODY_BYTES (checked while streaming, so a
    sender that lies about Content-Length is still cut off)."""
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_BODY_BYTES:
        return None
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_BODY_BYTES:
            return None
        chunks.append(chunk)
    return b"".join(chunks)


def create_app(secret: str, enqueue, store=None, now=None) -> FastAPI:
    if not secret:
        raise ValueError("A signing secret is required (read it from the environment).")
    store = store or MemoryStore()
    app = FastAPI()

    # No Pydantic model parameter on this route: FastAPI would parse the body before we verify it.
    @app.post("/webhooks")
    async def webhooks(request: Request):
        raw = await read_capped(request)
        if raw is None:
            return JSONResponse({"error": "too_large"}, status_code=413)

        # 1. Authenticity before anything else: an unverified request must not touch state.
        if not verify(raw, request.headers.get("webhook-signature"), secret, now() if now else None):
            return JSONResponse({"error": "invalid_signature"}, status_code=401)

        # 2. Parse only after verifying, from the same bytes.
        try:
            event = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            return JSONResponse({"error": "invalid_json"}, status_code=400)
        event_id = event.get("id") if isinstance(event, dict) else None
        if not isinstance(event_id, str) or not event_id or len(event_id) > 200:
            return JSONResponse({"error": "missing_event_id"}, status_code=400)

        # 3. Deduplicate: the sender retries, so the same event can arrive more than once.
        if not await store.first_time(event_id):
            return JSONResponse({"received": True, "duplicate": True})

        # 4. Acknowledge fast; the work happens elsewhere. If the hand-off fails, answer 500 so the
        #    sender retries (and make the store forget the id; see the webhook-idempotency skill).
        try:
            await enqueue(event)
        except Exception:  # noqa: BLE001 - any failure to hand off means "retry later"
            return JSONResponse({"error": "try_again"}, status_code=500)
        return JSONResponse({"received": True})

    return app


async def _log(event):
    print(f"queued {event['id']}")


if os.environ.get("WEBHOOK_SECRET"):
    app = create_app(os.environ["WEBHOOK_SECRET"], _log)
