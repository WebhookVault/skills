# Fixtures from real webhooks

## Capturing

- Use the sender's test or sandbox mode, and trigger each event type your handler supports.
- Keep the body bytes exactly, plus the headers your receiver reads (event type, delivery id, content
  type, signature header names). A pretty-printed copy is a different body.
- Record the sender's API version if it has one; payloads change between versions.

## Storing

```
tests/fixtures/
  shop/
    order-created.json          the body
    order-created.headers.json  the headers the receiver reads (no credentials)
    README.md                   when and how these were captured, API version
```

- One body per file, named by event type.
- Headers without credentials: drop authorization, cookies and signature values. Tests sign the body
  themselves.
- Scrub personal data with `scripts/scrub_fixture.py`, then read the result: it replaces emails,
  phone numbers and long digit runs, and keeps names, addresses and free text, which you must review.

## Keeping them current

- When the sender announces a new field or version, capture again and diff the new fixture against the
  old one. A handler that breaks on an added field is a bug worth a test of its own.
- Keep one deliberately old fixture per event type, to prove the handler still accepts payloads from
  before an upgrade if old events can still arrive (retries, replays).

## Synthetic fixtures

Hand-written payloads are fine for edge cases a sender rarely produces (a missing optional field, an
empty array, a very long string, non-ASCII text), as long as the common path is tested with real ones.
