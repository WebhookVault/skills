---
type: llm
---

The answer creates a short-lived endpoint through the WebhookVault API, triggers the signup, then blocks
on the await call until the webhook arrives and asserts on it. The API key comes from a CI secret (a Developer access
key), never written into the workflow file.
