---
max_turns: 16
allowed_tools: [Read, Glob, Grep, Skill]
tags: [general, idempotency]
---

Our Shopify order handler sometimes creates the same order twice. How do I stop that properly in Postgres?
