---
type: llm
---

The answer deduplicates on a stable id (for Shopify, X-Shopify-Webhook-Id or the order id), records it
under a unique constraint in the same database transaction as the order write (insert first, ON CONFLICT DO NOTHING),
and answers 2xx to a repeat. It does not rely on an in-memory set or a check-then-insert without a constraint.
