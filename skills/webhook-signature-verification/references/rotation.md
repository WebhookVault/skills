# Rotating a signing secret without dropping webhooks

A secret is replaced when it leaks, when someone with access leaves, or on a schedule. The danger is
the gap: requests signed with the old secret still arriving, or retried, after the receiver switched.

## The overlap pattern

1. Create the new secret at the sender. Many senders keep both active for a period and send two
   signatures in one header (two `v1=` entries, or two `v1,` entries), one per secret.
2. Configure the receiver with both secrets and accept a request when either verifies.
3. When the sender stops signing with the old secret (or its retries for older events have run
   out), remove the old one from the receiver.

```js
const secrets = [process.env.WEBHOOK_SECRET, process.env.WEBHOOK_SECRET_PREVIOUS].filter(Boolean);
const ok = secrets.some((secret) => verifyTimestampHeader({ body, header, secret }));
```

Keep both secrets in the secret store, never in code. Log which one matched (by name, never the
value) so you can see when the old one stops being used.

## Senders that sign with one secret only

When the sender switches immediately, rotate in a quiet period, accept both secrets for the length
of the sender's retry window, and expect some failed verifications for requests already in flight.
Those deliveries are retried by most senders; check that they succeeded.

## Public-key schemes

The sender rotates its key pair; the receiver updates the stored public key. Some senders publish
keys at a URL with key ids; cache them and refresh on an unknown id.
