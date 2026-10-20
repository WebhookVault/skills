# Examples: retries done right

The same retry logic in three languages, with no dependencies beyond each test framework:

- `isRetryableStatus`: network errors, timeouts, 408, 425, 429 and 5xx are retried; every other 4xx
  is a permanent answer.
- `backoffDelay`: exponential backoff with full jitter under a cap.
- `parseRetryAfter`: delay-seconds or an HTTP-date (RFC 9110), never negative, null when unreadable.
- `deliverWithRetries`: a delivery loop with an attempt budget and a time budget, ending in
  `delivered`, `rejected` or `dead_letter`.

| Folder | Run the tests |
|---|---|
| `node/` | `node --test` (Node.js 18 or later) |
| `python/` | `python -m unittest test_retry.py` (Python 3.9 or later) |
| `csharp/` | `dotnet test` (.NET 10 SDK) |

Randomness, the clock and sleep are passed in, so the tests check exact delays rather than ranges.
The HTTP-date test uses RFC 9110's own example, `Wed, 21 Oct 2015 07:28:00 GMT`.
