# PayPal webhook facts

Generated from `data/providers/paypal.json` by `tools/provider-facts.mjs`; change the data and regenerate, never this file.
Every fact was read from PayPal's own pages on the date shown, with the sentence it came from. Quotes are verbatim except that long dashes are written as hyphens. "not stated by the provider" means the pages read did not say; it does not mean there is no rule.

## Contents

- [Signature](#signature)
- [Delivery](#delivery)
- [Responding and retries](#responding-and-retries)
- [Events](#events)
- [Setup and testing](#setup-and-testing)
- [Pitfalls the provider warns about](#pitfalls-the-provider-warns-about)
- [In WebhookVault](#in-webhookvault)

## Signature

- **Signature header:** PAYPAL-TRANSMISSION-ID, PAYPAL-TRANSMISSION-TIME, PAYPAL-TRANSMISSION-SIG, PAYPAL-CERT-URL and PAYPAL-AUTH-ALGO
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/rest/](https://developer.paypal.com/api/rest/webhooks/rest/): "The unique ID of the transmission, from the paypal-transmission-id"
- **Scheme:** Asymmetric: RSA signature, SHA256withRSA, verified with the public key from the X.509 certificate at PAYPAL-CERT-URL. The signature header value is base64 (the sample listener decodes it with Buffer.from(sig, 'base64') and verifies with SHA256). No shared secret.
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/rest/](https://developer.paypal.com/api/rest/webhooks/rest/): "Use it to validate the signature given by the header paypal-transmission-sig"
- **Signed content:** the string transmissionId|timeStamp|webhookId|crc32 (four fields joined by the pipe character; the guide shows a trailing semicolon after the template). transmissionId = PAYPAL-TRANSMISSION-ID header; timeStamp = PAYPAL-TRANSMISSION-TIME header; webhookId = the ID of the subscribed webhook from the dashboard (not in headers or body); crc32 = CRC32 of the raw body as a decimal integer.
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/rest/](https://developer.paypal.com/api/rest/webhooks/rest/): "transmissionId | timeStamp | webhookId | crc32;"
- **Header format:** five separate headers (not one combined header); no multiple-signature list described
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/rest/](https://developer.paypal.com/api/rest/webhooks/rest/): "const signatureBuffer = Buffer.from(headers['paypal-transmission-sig'], 'base64');"
- **Where the secret comes from:** No secret. The webhook ID (needed to rebuild the signed string and for the verify API) is shown when the listener URL is subscribed, in Application management under the app's settings, or returned by the Webhooks Management API. The certificate is downloaded from PAYPAL-CERT-URL and may be cached.
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/rest/](https://developer.paypal.com/api/rest/webhooks/rest/): "When you subscribe a listener URL, it will have a Webhook ID. Record the ID as it is needed for verification of all webhook messages sent to that URL."
- **Secret scope:** webhook ID is per subscribed listener URL (up to 10 URLs per app); events are per app
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/](https://developer.paypal.com/api/rest/webhooks/): "Up to 10 webhook URLs may be subscribed per app."
- **Timestamp tolerance:** not stated by the provider
  Checked 2026-10-20 at [developer.paypal.com/api/rest/webhooks/rest/](https://developer.paypal.com/api/rest/webhooks/rest/).
- **Secret rotation:** not stated by the provider (certificate is downloaded from the header URL and cached; no rotation behaviour described)
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/rest/](https://developer.paypal.com/api/rest/webhooks/rest/): "This file should automatically be downloaded and cached for future use."
- **Raw body:** Use the original raw body for the CRC32; for the postback method, post webhook_event back byte-identical with no re-serialization.
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/rest/](https://developer.paypal.com/api/rest/webhooks/rest/): "It is essential that the webhook_event data be posted back exactly as it was received, with no deviations in formatting or content of any kind."
- **Header auth algo and cert url:** PAYPAL-AUTH-ALGO carries the algorithm (example value SHA256withRSA); PAYPAL-CERT-URL carries the certificate URL
  Read 2026-10-20 from [github.com/paypal/paypal-rest-api-specifications/blob/main/openapi/notifications_webhooks_v1.json](https://github.com/paypal/paypal-rest-api-specifications/blob/main/openapi/notifications_webhooks_v1.json): "Extract this value from the `PAYPAL-AUTH-ALGO` response header, which is received with the webhook notification."
- **Crc32 detail:** CRC32 of the raw HTTP body in decimal form; do not parse and re-stringify. The sample listener computes it as parseInt('0x' + crc32(rawBody).toString('hex')).
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/rest/](https://developer.paypal.com/api/rest/webhooks/rest/): "The Cyclic Redundancy Check (CRC32) checksum for the body of the HTTP payload, in decimal form. You must use the original raw body to calculate this"
- **Cert host restriction:** not stated by the provider. The guide's sample listener downloads whatever URL arrives in PAYPAL-CERT-URL without checking its host; the guide does not say which hosts a legitimate certificate comes from. (Example cert URL seen: https://api.sandbox.paypal.com/v1/notifications/certs/CERT-...)
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/rest/](https://developer.paypal.com/api/rest/webhooks/rest/): "const certPem = await downloadAndCache(headers['paypal-cert-url']);"
- **Verify api:** POST /v1/notifications/verify-webhook-signature (Bearer access token, JSON body). Required request fields: auth_algo (from PAYPAL-AUTH-ALGO), cert_url (PAYPAL-CERT-URL), transmission_id (PAYPAL-TRANSMISSION-ID, max 50), transmission_sig (PAYPAL-TRANSMISSION-SIG), transmission_time (PAYPAL-TRANSMISSION-TIME, RFC 3339), webhook_id (from the developer portal, max 50), webhook_event (the event body). Response: {verification_status: SUCCESS | FAILURE}. Hosts shown: api.sandbox.paypal.com for sandbox, api-m.paypal.com for live. Not usable for simulator mock events.
  Read 2026-10-20 from [github.com/paypal/paypal-rest-api-specifications/blob/main/openapi/notifications_webhooks_v1.json](https://github.com/paypal/paypal-rest-api-specifications/blob/main/openapi/notifications_webhooks_v1.json): "The status of the signature verification."
- **Verify api guide quote:** the guide's curl example for the postback method
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/rest/](https://developer.paypal.com/api/rest/webhooks/rest/): "curl -X POST https://api.sandbox.paypal.com/v1/notifications/verify-webhook-signature"
- **Preferred method:** PayPal says self verification (CRC32 + certificate) is preferred when the system can do it, as it is faster and avoids an extra API dependency; postback is the alternative.
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/rest/](https://developer.paypal.com/api/rest/webhooks/rest/): "self cryptographic verification is the preferred method as it will be faster and avoid extra API dependency and latency."
- **Mock event webhook id:** For simulator (mock) events, self verification uses the literal webhook ID string WEBHOOK_ID
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/rest/](https://developer.paypal.com/api/rest/webhooks/rest/): "For message signature verification purposes, the ID of mock webhooks is the string: WEBHOOK_ID"
- **Official helper (Node.js):** not stated by the provider (the guide gives a hand-written Express sample using crypto.createVerify('SHA256') and buffer-crc32, not an SDK helper)
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/rest/](https://developer.paypal.com/api/rest/webhooks/rest/): "const verifier = crypto.createVerify('SHA256');"
- **Official helper (Python):** not stated by the provider
  Checked 2026-10-20 at [developer.paypal.com/api/rest/webhooks/rest/](https://developer.paypal.com/api/rest/webhooks/rest/).
- **Official helper (.NET):** not stated by the provider
  Checked 2026-10-20 at [developer.paypal.com/api/rest/webhooks/rest/](https://developer.paypal.com/api/rest/webhooks/rest/).

## Delivery

- **Method and content type:** HTTPS POST to a listener on port 443 only. Content-Type not stated in words; the guide's sample listener reads the body with express.raw({type: 'application/json'}) and JSON.parse.
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/](https://developer.paypal.com/api/rest/webhooks/): "Webhooks are HTTPS posts from PayPal to an endpoint on your server whenever the corresponding event type occurs"
- **Event name:** body JSON field event_type (for example PAYMENT.CAPTURE.COMPLETED); also resource_type, event_version, resource_version, summary, resource, links, create_time
  Read 2026-10-20 from [github.com/paypal/paypal-rest-api-specifications/blob/main/openapi/notifications_webhooks_v1.json](https://github.com/paypal/paypal-rest-api-specifications/blob/main/openapi/notifications_webhooks_v1.json): "The event that triggered the webhook event notification."
- **Delivery or event id:** event id: body field id (for example WH-3F562076HD293871E-75F399086E414290U); the transmission id header differs per transmission attempt per PayPal's description 'ID of the HTTP transmission'. PayPal's pages do not explicitly tell receivers which to dedupe on.
  Read 2026-10-20 from [github.com/paypal/paypal-rest-api-specifications/blob/main/openapi/notifications_webhooks_v1.json](https://github.com/paypal/paypal-rest-api-specifications/blob/main/openapi/notifications_webhooks_v1.json): "The ID of the webhook event notification."
- **Handshake:** not stated by the provider
  Checked 2026-10-20 at [developer.paypal.com/api/rest/webhooks/](https://developer.paypal.com/api/rest/webhooks/).
- **Events per request:** one event per message; each message is posted to every subscribed listener URL
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/](https://developer.paypal.com/api/rest/webhooks/): "Messages for events will be posted to every subscribed listener URL."
- **Resource version:** body field resource_version (string, example 2.0) versions the shape of the resource object; event_version (example 1.0) is marked deprecated in the spec. The guide does not describe resource_version in prose.
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/rest/](https://developer.paypal.com/api/rest/webhooks/rest/): ""event_version":"1.0","create_time":"2024-05-16T05:19:19.355Z","resource_type":"capture","resource_version":"2.0","event_type":"PAYMENT.CAPTURE.COMPLETED""

## Responding and retries

- **Expected response:** HTTP 200 or any other 2xx; any non-2xx triggers retry
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/](https://developer.paypal.com/api/rest/webhooks/): "Successful receipt requires your listener endpoint to respond with an HTTP 200 or other 2xx status code."
- **Response deadline:** not stated by the provider
  Checked 2026-10-20 at [developer.paypal.com/api/rest/webhooks/](https://developer.paypal.com/api/rest/webhooks/).
- **Retries:** up to 25 attempts over 3 days, or until a 2xx arrives; per-attempt schedule not given. After 3 days the delivery is marked Failed and can be resent manually from the Webhook Events dashboard (or via the resend event notification API).
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/](https://developer.paypal.com/api/rest/webhooks/): "Any non-2xx status code will cause PayPal to reattempt delivery up to 25 times over the course of 3 days or until it receives a 2xx success code."
- **Disabling after failures:** not stated by the provider
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/](https://developer.paypal.com/api/rest/webhooks/): "If unsuccessful after 3 days, delivery will be marked as Failed (but can be resent again manually from the Webhook Events dashboard)."
- **Ordering:** not stated by the provider
  Checked 2026-10-20 at [developer.paypal.com/api/rest/webhooks/](https://developer.paypal.com/api/rest/webhooks/).
- **Duplicates:** not stated by the provider (retries and manual resends exist, so duplicates are possible, but PayPal's pages do not say so)
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/rest/](https://developer.paypal.com/api/rest/webhooks/rest/): "PayPal will retry each delivery up to 25 times over 3 days."

## Events

Full list: https://developer.paypal.com/api/rest/webhooks/event-names/

- **`PAYMENT.CAPTURE.COMPLETED`:** a payment capture completed (Payments v2)
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/event-names/](https://developer.paypal.com/api/rest/webhooks/event-names/): "A payment capture completes."
- **`PAYMENT.CAPTURE.DENIED`:** a payment capture was denied (listed under Payments v1)
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/event-names/](https://developer.paypal.com/api/rest/webhooks/event-names/): "A payment capture is denied."
- **`PAYMENT.CAPTURE.DECLINED`:** a payment capture was declined (listed under Payments v2); both DENIED and DECLINED appear in the docs
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/event-names/](https://developer.paypal.com/api/rest/webhooks/event-names/): "A payment capture is declined."
- **`PAYMENT.CAPTURE.REFUNDED`:** a merchant refunded a capture
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/event-names/](https://developer.paypal.com/api/rest/webhooks/event-names/): "A merchant refunds a payment capture."
- **`PAYMENT.CAPTURE.REVERSED`:** PayPal reversed a capture
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/event-names/](https://developer.paypal.com/api/rest/webhooks/event-names/): "PayPal reverses a payment capture."
- **`CHECKOUT.ORDER.APPROVED`:** buyer approved an order; ready to capture
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/event-names/](https://developer.paypal.com/api/rest/webhooks/event-names/): "A buyer approved a checkout order"
- **`BILLING.SUBSCRIPTION.ACTIVATED`:** subscription activated
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/event-names/](https://developer.paypal.com/api/rest/webhooks/event-names/): "A subscription is activated."
- **`BILLING.SUBSCRIPTION.CANCELLED`:** subscription cancelled
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/event-names/](https://developer.paypal.com/api/rest/webhooks/event-names/): "A subscription is cancelled."
- **`BILLING.SUBSCRIPTION.PAYMENT.FAILED`:** a subscription payment failed
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/event-names/](https://developer.paypal.com/api/rest/webhooks/event-names/): "Payment failed on subscription."
- **`PAYMENT.SALE.COMPLETED`:** a sale completed (for example each subscription cycle payment)
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/event-names/](https://developer.paypal.com/api/rest/webhooks/event-names/): "A sale completes."
- **`CUSTOMER.DISPUTE.CREATED`:** a dispute was opened; supersedes and deprecates RISK.DISPUTE.CREATED
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/event-names/](https://developer.paypal.com/api/rest/webhooks/event-names/): "A dispute is created."

## Setup and testing

- **Where the URL goes:** Application management (developer dashboard), under each app's settings, or the Webhooks Management API. Up to 10 URLs per app; subscribe specific event types or * for all. Listener must be HTTPS on port 443.
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/rest/](https://developer.paypal.com/api/rest/webhooks/rest/): "Your listener should be an app or script deployed at the corresponding URL that listens on HTTPS port 443."
- **Test tools:** Webhooks simulator (post a mock event to any listener on HTTPS 443; also POST /v1/notifications/simulate-event). Mock events: not tied to an app, not in the dashboard event viewer, cannot be resent, cannot be verified with the verify-webhook-signature postback, self-verify with webhook ID WEBHOOK_ID. Sandbox: subscribe the listener to a sandbox REST app and generate real test events. Real events can be resent from the Webhook Events dashboard.
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/simulator/](https://developer.paypal.com/api/rest/webhooks/simulator/): "They cannot be verified by posting back to the PayPal verify-webhook-signature endpoint"
- **Source IP addresses:** not stated by the provider
  Checked 2026-10-20 at [developer.paypal.com/api/rest/webhooks/rest/](https://developer.paypal.com/api/rest/webhooks/rest/).

Notes from reading these pages (our words, not the provider's):

- Event names page lists PAYMENT.CAPTURE.DENIED under Payments v1 and PAYMENT.CAPTURE.DECLINED under Payments v2; both exist in the docs.
- BILLING.SUBSCRIPTION.CANCELLED is listed twice, as 'A billing agreement is canceled' (legacy billing plans and agreements) and as 'A subscription is cancelled' (Subscriptions).

## Pitfalls the provider warns about

- **1:** PayPal only delivers to HTTPS port 443.
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/rest/](https://developer.paypal.com/api/rest/webhooks/rest/): "PayPal only delivers webhooks to port 443 (HTTPS)."
- **2:** If you do not verify, nothing proves the sender is PayPal.
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/](https://developer.paypal.com/api/rest/webhooks/): "If you do not verify a message, you will not have a way to validate that its sender was in fact PayPal."
- **3:** The webhook ID is not in the headers or body; you must store it from the subscription config.
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/rest/](https://developer.paypal.com/api/rest/webhooks/rest/): "This does not come in the header or body of the message but rather where the webhook listener URL's event subscriptions are configured"
- **4:** Delivery can fail with no HTTP status at all if a firewall blocks port 443 or the domain is categorised as malware or abusive by URL filtering services.
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/rest/](https://developer.paypal.com/api/rest/webhooks/rest/): "if the domain webhooks are being sent to is marked as malware, phishing, or as involved in some other abuse by url filtering services."
- **5:** Events only arrive for the specific app the URL is subscribed on; the legacy NVP/SOAP app is separate and excludes NVP/SOAP recurring payments.
  Read 2026-10-20 from [developer.paypal.com/api/rest/webhooks/](https://developer.paypal.com/api/rest/webhooks/): "Only events associated with the specific app will be received"

Pages that could not be read when these facts were taken:

- https://developer.paypal.com/docs/api/webhooks/v1/: client-rendered shell; only endpoint titles visible; request fields taken from PayPal's own OpenAPI spec repo instead

## In WebhookVault

What WebhookVault does with PayPal requests, read from its provider catalogue on 2026-10-20. These are facts about WebhookVault, not about PayPal.

- **Signature header it reads:** `PAYPAL-TRANSMISSION-SIG`
- **Checks the signature:** no. Certificate-chain signature (PAYPAL-TRANSMISSION-SIG); WebhookVault does not check this scheme yet, so a capture shows the verdict as unverifiable with the scheme named
- **Secret field label:** Secret
- **Where it finds the event name:** body `event_type`
- **Where the capture URL goes in PayPal:** Developer Dashboard > Apps and Credentials > your app > Webhooks
