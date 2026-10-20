# SendGrid webhook facts

Generated from `data/providers/sendgrid.json` by `tools/provider-facts.mjs`; change the data and regenerate, never this file.
Every fact was read from SendGrid's own pages on the date shown, with the sentence it came from. Quotes are verbatim except that long dashes are written as hyphens. "not stated by the provider" means the pages read did not say; it does not mean there is no rule.

## Contents

- [Signature](#signature)
- [Delivery](#delivery)
- [Responding and retries](#responding-and-retries)
- [Events](#events)
- [Setup and testing](#setup-and-testing)
- [Pitfalls the provider warns about](#pitfalls-the-provider-warns-about)
- [Conflicting or product-specific rules](#conflicting-or-product-specific-rules)
- [In WebhookVault](#in-webhookvault)

## Signature

- **Signature header:** X-Twilio-Email-Event-Webhook-Signature, with the timestamp in X-Twilio-Email-Event-Webhook-Timestamp
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features): "The private key will be used to generate a signature that is posted to your HTTP webhook in the X-Twilio-Email-Event-Webhook-Signature header."
- **Scheme:** ECDSA (Elliptic Curve Digital Signature Algorithm) over a SHA-256 hash; signature is Base64 of an ASN.1 (r,s) structure. The page does not name the curve.
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features): "Twilio SendGrid generates the private and public key pair using the Elliptic Curve Digital Signature Algorithm (ECDSA)."
- **Signed content:** SHA-256 hash of the timestamp header value concatenated with the raw payload bytes (timestamp first, no separator), then ECDSA-verified against that digest
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features): "Generate a sha256 hash of the timestamp + payload (use raw bytes)."
- **Header format:** Single Base64 signature in one header; separate header for the timestamp
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features): "Get the signature from the "X-Twilio-Email-Event-Webhook-Signature" HTTP header."
- **Where the secret comes from:** A public verification key shown in the webhook's settings dialog after you enable Signed Event Webhook and Save (Settings > Mail Settings > Webhook Settings > Event Webhooks, edit, Security features). The key pair is only generated on Save. Can also be managed via the Event Webhook API.
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features): "You must click Save in order to generate a verification key and enable signature verification."
- **Secret scope:** Per Event Webhook configuration (the key pair belongs to a webhook; you can have several webhooks). The page says disabling deletes that webhook's key pair.
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features): "To disable signature verification, which will delete the Webhook's existing key pair:"
- **Timestamp tolerance:** not stated by the provider (the timestamp is signed, but no window is given)
  Checked 2026-10-20 at [www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features).
- **Secret rotation:** not stated by the provider. Turning signature verification off and saving deletes the webhook's key pair.
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features): "Your key pair will not be deleted until you click Save."
- **Raw body:** Payload must be used in its raw bytes form; converting to a JSON string can remove characters that were part of the signed bytes
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features): "Transformations from raw bytes to a JSON string may remove characters that were used as part of the generated signature."
- **Decoding:** Base64-decode the header value, then ASN.1 unmarshal into the r and s values
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features): "Decode the Base64 encoded signature. Then perform an ASN.1 unmarshal of the decoded signature into a string."
- **Public key format:** The docs page does not state the encoding. Official SDK helpers take the key as the bare base64 string shown in the UI (no PEM header lines): the Python helper wraps it in BEGIN/END PUBLIC KEY lines before loading, i.e. a base64 DER SubjectPublicKeyInfo.
  Read 2026-10-20 from [raw.githubusercontent.com/sendgrid/sendgrid-python/main/sendgrid/helpers/eventwebhook/__init__.py](https://raw.githubusercontent.com/sendgrid/sendgrid-python/main/sendgrid/helpers/eventwebhook/__init__.py): "pem_key = "-----BEGIN PUBLIC KEY-----\n" + public_key + "\n-----END PUBLIC KEY-----""
- **Oauth alternative:** OAuth 2.0 Client Credentials is a separate option: SendGrid sends the access token in an Authorization header. On an invalid or expired token the endpoint must return 4xx with invalid_request, invalid_token or insufficient_scope in the body so SendGrid fetches a new token and retries.
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features): "Upon receiving any of these error codes from your webhook, SendGrid will request a new OAuth token from your OAuth service and retry the webhook."
- **Sdk test vector note:** The docs print no worked example. The official Python library's unit test has one; its payload ends with a carriage return and newline, which the test comment stresses.
  Read 2026-10-20 from [raw.githubusercontent.com/sendgrid/sendgrid-python/main/test/unit/test_eventwebhook.py](https://raw.githubusercontent.com/sendgrid/sendgrid-python/main/test/unit/test_eventwebhook.py): "# Be sure to include the trailing carriage return and newline!"
- **Official helper (Node.js):** EventWebhook class in the Node.js library: new EventWebhook(); convertPublicKeyToECDSA(publicKey); verifySignature(publicKey, payload, signature, timestamp). Header-name constants via EventWebhookHeader.SIGNATURE() and EventWebhookHeader.TIMESTAMP(). Source computes timestamp + payload then verifies the Base64 signature.
  Read 2026-10-20 from [raw.githubusercontent.com/sendgrid/sendgrid-nodejs/main/packages/eventwebhook/src/eventwebhook.js](https://raw.githubusercontent.com/sendgrid/sendgrid-nodejs/main/packages/eventwebhook/src/eventwebhook.js): "verifySignature(publicKey, payload, signature, timestamp) {"
- **Official helper (Python):** from sendgrid import EventWebhook; ew = EventWebhook(); key = ew.convert_public_key_to_ecdsa(public_key); ew.verify_signature(payload, signature, timestamp, key). Source: (timestamp + payload).encode, base64.b64decode(signature), ECDSA with SHA256.
  Read 2026-10-20 from [raw.githubusercontent.com/sendgrid/sendgrid-python/main/sendgrid/helpers/eventwebhook/__init__.py](https://raw.githubusercontent.com/sendgrid/sendgrid-python/main/sendgrid/helpers/eventwebhook/__init__.py): "def verify_signature(self, payload, signature, timestamp, public_key=None):"
- **Official helper (.NET):** SendGrid.Helpers.EventWebhook.RequestValidator: ConvertPublicKeyToECDSA(publicKey); VerifySignature(ecPublicKey, requestBody, signature, timestamp); constants RequestValidator.SIGNATURE_HEADER and TIMESTAMP_HEADER.
  Read 2026-10-20 from [raw.githubusercontent.com/sendgrid/sendgrid-csharp/main/src/SendGrid/Helpers/EventWebhook/RequestValidator.cs](https://raw.githubusercontent.com/sendgrid/sendgrid-csharp/main/src/SendGrid/Helpers/EventWebhook/RequestValidator.cs): "public bool VerifySignature(PublicKey publicKey, string payload, string signature, string timestamp)"
- **Official helper (Docs listing):** The docs say the API libraries for C#, Go, Java, Node.js, PHP, Python and Ruby carry Event Webhook verification helpers.
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features): "The Twilio SendGrid API libraries contain helpers to assist you when verifying the ECDSA signature."

## Delivery

- **Method and content type:** HTTP POST with a JSON array of events (Content-Type application/json in the docs' curl example)
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/twilio-sendgrid-event-webhook-overview](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/twilio-sendgrid-event-webhook-overview): "--header "Content-Type: application/json""
- **Event name:** event property on each event object
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/event](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/event): "event Enum(String) Type of occurrence that triggered this event."
- **Delivery or event id:** sg_event_id on each event: URL-safe Base64url string, at most 100 characters, unique per event; use for deduplication. (sg_message_id identifies the message, not the event.)
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/event](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/event): "Unique ID that Twilio attached to this event. These URL-safe IDs can be no more than 100 characters long. Use this ID for deduplication purposes."
- **Handshake:** not stated by the provider (no setup handshake; a Test Your Integration button posts example events)
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook): "Click this button to receive an HTTP POST request at your specified Post URL containing a JSON array of example events."
- **Events per request:** Arrays of events. Events post within approximately 30 seconds or when the batch size reaches 768 kilobytes, per server.
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/twilio-sendgrid-event-webhook-overview](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/twilio-sendgrid-event-webhook-overview): "Events post within approximately 30 seconds or when the batch size reaches 768 kilobytes."

## Responding and retries

- **Expected response:** Any 2xx response
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook): "If your web server does not return a 2xx response type, SendGrid will retry the POST request until it receives a 2xx response or the maximum time has elapsed."
- **Response deadline:** not stated by the provider
  Checked 2026-10-20 at [www.twilio.com/docs/sendgrid/for-developers/tracking-events/twilio-sendgrid-event-webhook-overview](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/twilio-sendgrid-event-webhook-overview).
- **Retries:** A non-2xx answer is retried at increasing intervals for up to 24 hours after the event occurred (a rolling 24 hours per event). The intervals and count are not stated.
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook): "All events are re-tried at increasing intervals for up to 24 hours after the event occurs. This time limit is a rolling 24 hours"
- **Disabling after failures:** not stated by the provider for a failing endpoint (the overview mentions disabling only when a plan is downgraded)
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/twilio-sendgrid-event-webhook-overview](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/twilio-sendgrid-event-webhook-overview): "Automatic disabling during a downgrade is determined by the Created Date."
- **Ordering:** not stated by the provider
  Checked 2026-10-20 at [www.twilio.com/docs/sendgrid/for-developers/tracking-events/twilio-sendgrid-event-webhook-overview](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/twilio-sendgrid-event-webhook-overview).
- **Duplicates:** Duplicate events can arrive; SendGrid recommends deduplicating on sg_event_id
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/twilio-sendgrid-event-webhook-overview](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/twilio-sendgrid-event-webhook-overview): "It's possible to see duplicate events in the data posted by the Event Webhook."

## Events

Full list: https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/event

- **Event values quote:** processed, dropped, delivered, deferred, bounce, open, click, spam report, unsubscribe, group_unsubscribe, group_resubscribe
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/event](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/event): "Expects: processed, dropped, delivered, deferred, bounce, open, click, spam report, unsubscribe, group_unsubscribe, and group_resubscribe."

- **`processed`:** SendGrid accepted the message for delivery
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/event](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/event): "bounced, delivered, deferred, dropped, or processed."
- **`delivered`:** The receiving server accepted the message
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/event](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/event): "bounced, delivered, deferred, dropped, or processed."
- **`deferred`:** The receiving server temporarily refused the message; SendGrid keeps trying
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/event](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/event): "bounced, delivered, deferred, dropped, or processed."
- **`bounce`:** Hard bounce: receiving server does not accept mail for the recipient (type bounce)
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/event](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/event): "The receiving server doesn't accept mail sent to this recipient."
- **`dropped`:** SendGrid dropped the message (for example prior unsubscribe or bounce)
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/event](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/event): "Twilio SendGrid dropped the message for one of the following reasons:"
- **`open`:** Recipient opened the HTML message (requires Open Tracking); sg_machine_open flags Apple Mail Privacy Protection opens
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/event](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/event): "Recipient has opened the HTML message. To track opens, turn on Open Tracking."
- **`click`:** Recipient clicked a tracked link (requires Click Tracking)
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/event](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/event): "Recipient clicked on a link within the message. To track clicks, turn on Click Tracking."
- **`spamreport`:** The recipient marked the message as spam (see the conflict note on the name)
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/event](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/event): "Recipient marked message as spam."
- **`unsubscribe`:** Recipient used the Opt Out of All Emails link
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/event](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/event): "Recipient clicked on the Opt Out of All Emails link."
- **`group_unsubscribe`:** Recipient unsubscribed from a specific group
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/event](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/event): "Recipient unsubscribed from a specific group."
- **`group_resubscribe`:** Recipient resubscribed to a specific group
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/event](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/event): "Recipient resubscribed to a specific group by updating their preferences."

## Setup and testing

- **Where the URL goes:** SendGrid UI: Settings > Mail Settings > Webhook Settings > Event Webhooks > Create new webhook; fields Post URL and Actions to be posted are required. Also manageable with the Webhooks API.
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook): "Only the Post URL and Actions to be posted fields are required."
- **Test tools:** Test Your Integration button in the webhook dialog posts example events (no real mail data). Signature verification is not tested if you click it before the first Save.
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features): "If you click Test Integration before clicking Save, signature verification will not be tested because the key pair is only generated once the Webhook is saved."
- **Source IP addresses:** No ranges published on the pages read; the page warns the IPs change often and not to block them
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/twilio-sendgrid-event-webhook-overview](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/twilio-sendgrid-event-webhook-overview): "Our IPs often change because we constantly add more machines."

## Pitfalls the provider warns about

- **1:** Verify against raw bytes; re-serialised JSON breaks the signature.
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features): "we deliver a payload that must be used in its raw bytes form."
- **2:** Duplicates happen; dedupe on sg_event_id.
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/twilio-sendgrid-event-webhook-overview](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/twilio-sendgrid-event-webhook-overview): "We recommend using some form of deduplication when processing or storing your Event Webhook data using the sg_event_id as a differentiator."
- **3:** High-volume senders can produce tens or hundreds of posts per second; load test the receiver.
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/twilio-sendgrid-event-webhook-overview](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/twilio-sendgrid-event-webhook-overview): "the webhook URL may post tens or even hundreds of posts per second."
- **4:** Do not block SendGrid IPs; they change often.
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/twilio-sendgrid-event-webhook-overview](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/twilio-sendgrid-event-webhook-overview): "Make sure you are not blocking the SendGrid IP addresses that are trying to POST to your server."
- **5:** The v2 eventnotify API call overwrites existing Event Webhook settings, including OAuth 2.0.
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features): "Using the v2 Web API's eventnotify API call will overwrite any previously configured Event Webhook notification settings, including OAuth 2.0."
- **6:** Categories and unique arguments are stored as not-PII; never put personal data in them.
  Read 2026-10-20 from [www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook](https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook): "You should take care not to place PII in this field."

## Conflicting or product-specific rules

- **The spam report event name:** The property table and its list of expected values write "spam report" with a space, while the example payload has "spamreport". Accept both until SendGrid settles it.
  - Read 2026-10-20 from https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/event: "open, click, spam report, unsubscribe, and group_unsubscribe, and group_resubscribe."
  - Read 2026-10-20 from https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/event: ""event" : "spamreport""

## In WebhookVault

What WebhookVault does with SendGrid requests, read from its provider catalogue on 2026-10-20. These are facts about WebhookVault, not about SendGrid.

- **Signature header it reads:** `X-Twilio-Email-Event-Webhook-Signature`
- **Checks the signature:** yes (ECDSA P-256 over timestamp + body, verified with the public key)
- **Secret field label:** Verification public key (base64)
- **Where it finds the event name:** body `event`
- **Where the capture URL goes in SendGrid:** Settings > Mail Settings > Event Webhook
