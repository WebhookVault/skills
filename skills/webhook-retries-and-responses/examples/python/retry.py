"""Retrying a webhook delivery (or any call to a receiver) safely: exponential backoff with full
jitter under a cap, retry only what can succeed later, honour Retry-After, give up after a budget and
park the delivery as a dead letter. Standard library only.

Randomness, the clock and sleep are parameters so the behaviour is testable exactly.
"""

import random as _random
import re
import time
from email.utils import parsedate_to_datetime

_HTTP_DATE = re.compile(r"^[A-Za-z]{3}, \d{2} [A-Za-z]{3} \d{4} \d{2}:\d{2}:\d{2} GMT$")


def is_retryable_status(status: int) -> bool:
    """Statuses worth retrying: the receiver may succeed later. Every other 4xx is permanent."""
    return status in (408, 425, 429) or 500 <= status <= 599


def backoff_delay(attempt: int, base_ms=1000, cap_ms=15 * 60 * 1000, random=_random.random) -> int:
    """Full jitter: a random delay in [0, min(cap, base * 2**attempt)) milliseconds; attempt from 0."""
    if not isinstance(attempt, int) or attempt < 0:
        raise ValueError("attempt is a whole number from 0")
    ceiling = min(cap_ms, base_ms * 2 ** min(attempt, 30))
    return int(random() * ceiling)


def parse_retry_after(value, now_ms=None):
    """Retry-After (RFC 9110 10.2.3) in milliseconds: delay-seconds or an HTTP-date. None when absent
    or unreadable; never negative."""
    if not isinstance(value, str):
        return None
    v = value.strip()
    if v.isdigit():
        return int(v) * 1000
    if not _HTTP_DATE.match(v):
        return None
    try:
        at_ms = int(parsedate_to_datetime(v).timestamp() * 1000)
    except (TypeError, ValueError):
        return None
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    return max(0, at_ms - now_ms)


def deliver_with_retries(send, max_attempts=8, base_ms=1000, cap_ms=15 * 60 * 1000, max_elapsed_ms=60 * 60 * 1000,
                         random=_random.random, sleep=lambda ms: time.sleep(ms / 1000), now=lambda: int(time.time() * 1000)):
    """Calls send() -> (status, headers dict with lower-case names), retrying as above. A raised
    exception counts as a network error (retryable). Returns (outcome, attempts, status) with outcome
    "delivered", "rejected" or "dead_letter"."""
    started = now()
    status = None
    made = 0
    for attempt in range(1, max_attempts + 1):
        made = attempt
        retry_after_ms = None
        try:
            status, headers = send()
            if 200 <= status <= 299:
                return "delivered", attempt, status
            if not is_retryable_status(status):
                return "rejected", attempt, status
            retry_after_ms = parse_retry_after((headers or {}).get("retry-after"), now())
        except Exception:  # noqa: BLE001 - a network error or timeout: retry
            status = None
        if attempt == max_attempts:
            break
        wait = retry_after_ms if retry_after_ms is not None else backoff_delay(attempt - 1, base_ms, cap_ms, random)
        if now() - started + wait > max_elapsed_ms:
            break
        sleep(wait)
    return "dead_letter", made, status
