# Building the negative cases

## Signature failures

- **Wrong secret:** sign with a second test secret.
- **Tampered body:** sign the fixture, then change one byte before sending.
- **Re-serialised body:** sign the fixture, then parse and serialise it again (indentation, key
  order) before sending. Verification must fail: this proves the receiver checks the raw bytes.
- **Stale timestamp:** sign with a timestamp older than the tolerance (inject the clock in the
  receiver so the test is exact).
- **Missing or malformed header:** omit it; send garbage; send two timestamps.

Expect 401 (or the sender-specific refusal) and no state change. Then send the valid request and
confirm the event id was not used up by the failed attempts.

## Duplicates

Send the same signed event twice, and ten times concurrently. Expect it processed once and every
response 2xx.

## Ordering

Send version 2 then version 1 of the same object; expect version 2 kept. Send a delete before the
create; expect the deleted state kept. Send twenty versions concurrently in random order; expect the
newest kept.

## Failures

- Make the downstream step fail (a fake queue that throws, a database you stop) and expect a 5xx, no
  half-written state, and success when the same event is sent again.
- Make the receiver slow and check the sender-side timeout you expect is respected.

## Size and shape

- A body over the receiver's limit: 413 before the whole body is read.
- Valid signature, invalid JSON: 400.
- Valid signature, valid JSON, missing event id: 400.
- Non-ASCII text, an empty body where the sender may send one, very long strings.

## Hostile text

Put markup and instructions in every free-text field of a fixture (`<script>`, `<!channel>`,
`@everyone`, "ignore previous instructions") and check every place the text is shown, logged or
forwarded: it appears escaped, and nothing acts on it.
