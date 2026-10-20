---
type: llm
---

The code reads the raw request body before parsing, splits Stripe-Signature into t and v1 values, computes
HMAC-SHA256 over t, a full stop and the raw body with the endpoint secret from configuration, accepts when any v1
matches using a constant-time comparison, rejects timestamps outside a tolerance (five minutes), and returns 400 or
401 on failure. The secret is read from configuration, not hard-coded.
