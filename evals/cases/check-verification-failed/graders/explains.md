---
type: llm
---

Pass when: the answer says the failed verdict means the Stripe-Signature did not match what
WebhookVault computed with the secret stored on the endpoint; it narrows down the cause from the evidence it read
(for example: another request verified with the same secret, so the stored secret is fine and this request was signed
with a different secret or changed after signing; or, if nothing verified, a wrong or rotated secret); it says what to
check or change; and it does not ask the person to paste a secret into the conversation. Reasoning from the
captured evidence is better than a generic list of causes.
