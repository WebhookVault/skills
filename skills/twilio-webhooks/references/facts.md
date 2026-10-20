# Twilio webhook facts

Generated from `data/providers/twilio.json` by `tools/provider-facts.mjs`; change the data and regenerate, never this file.
Every fact was read from Twilio's own pages on the date shown, with the sentence it came from. Quotes are verbatim except that long dashes are written as hyphens. "not stated by the provider" means the pages read did not say; it does not mean there is no rule.

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

- **Signature header:** X-Twilio-Signature
  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/webhooks-security](https://www.twilio.com/docs/usage/webhooks/webhooks-security): "Twilio signs all HTTP requests to your app with an X-Twilio-Signature HTTP header."
- **Scheme:** HMAC-SHA1 keyed with the account auth token, then Base64-encoded
  Read 2026-10-20 from [www.twilio.com/docs/usage/security](https://www.twilio.com/docs/usage/security): "Sign the resulting string with HMAC-SHA1 using your AuthToken as the key (remember, your AuthToken's case matters!)."
- **Signed content:** Form-encoded POST: the full request URL (scheme through end of query string, including port per the port rules below), followed by each POST parameter name and value appended with no delimiters, parameters sorted alphabetically by name (Unix-style case-sensitive order). GET: the final URL includes the parameters in the query string. JSON body (application/json): Twilio appends a bodySHA256 query parameter (hex SHA-256 of the raw body) to the URL and the signature covers the URL including it; do not treat JSON properties as form parameters.
  Read 2026-10-20 from [www.twilio.com/docs/usage/security](https://www.twilio.com/docs/usage/security): "Iterate through the sorted list of POST parameters, and append the variable name and value (with no delimiters) to the end of the URL string."
- **Header format:** Single header value: the Base64 signature, e.g. L/OH5YylLD5NRKLltdqwSvS0BnU=
  Read 2026-10-20 from [www.twilio.com/docs/usage/security](https://www.twilio.com/docs/usage/security): "Finally, compare that to the hash Twilio sent in the X-Twilio-Signature HTTP header."
- **Where the secret comes from:** The Twilio account's primary Auth Token (Console). Alternatively, the Webhooks configuration API can sign requests with a key you manage instead of the auth token.
  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/webhooks-overview](https://www.twilio.com/docs/usage/webhooks/webhooks-overview): "Sign requests with a key you manage instead of your account authentication token."
- **Secret scope:** The account's auth token (subaccounts are not discussed on the pages read)
  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/webhooks-security](https://www.twilio.com/docs/usage/webhooks/webhooks-security): "Twilio hashes the signature with the HMAC-SHA1 hashing algorithm using your account auth token as the secret key."
- **Timestamp tolerance:** not stated by the provider (the signature covers no timestamp, so it cannot expire)
  Checked 2026-10-20 at [www.twilio.com/docs/usage/security](https://www.twilio.com/docs/usage/security).
- **Secret rotation:** Use the primary Auth Token as the key; if a secondary token was recently created, keep using the previous (primary) token until the secondary is promoted
  Read 2026-10-20 from [www.twilio.com/docs/usage/security](https://www.twilio.com/docs/usage/security): "If you have recently created a secondary AuthToken, you still need to use your previous AuthToken until the secondary one has been promoted to your primary AuthToken."
- **Raw body:** For JSON requests use the raw body string with the JSON-specific method. For form requests pass every received parameter, not a hardcoded list. Some frameworks trim whitespace in POST fields (for example Laravel TrimStrings, certain Node.js middleware), which breaks matching.
  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/webhooks-security](https://www.twilio.com/docs/usage/webhooks/webhooks-security): "Use your SDK's JSON-specific validation method (for example, validateRequestWithBody) and pass the raw request body string."
- **Scheme encoding:** Base64 of the raw HMAC-SHA1 digest
  Read 2026-10-20 from [www.twilio.com/docs/usage/security](https://www.twilio.com/docs/usage/security): "Base64-encode the resulting hash value."
- **Signed content sort:** Unix-style case-sensitive sorting by parameter name
  Read 2026-10-20 from [www.twilio.com/docs/usage/security](https://www.twilio.com/docs/usage/security): "sort all the POST parameters alphabetically (using Unix-style case-sensitive sorting order)."
- **Signed content json:** For application/json, Twilio adds bodySHA256 to the URL; the SDK checks the body hash against it and includes it in the signature calculation
  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/webhooks-security](https://www.twilio.com/docs/usage/webhooks/webhooks-security): "For these requests, Twilio appends a bodySHA256 query parameter to your webhook URL. The parameter value is a SHA-256 hash of the raw JSON request body."
- **Bodysha256 encoding:** hexadecimal representation of the SHA-256 hash of the request body
  Read 2026-10-20 from [www.twilio.com/docs/usage/security](https://www.twilio.com/docs/usage/security): "Its value is calculated as the hexadecimal representation of the SHA-256 hash of the request body."
- **Url exactness:** Pass the exact URL Twilio used, including query string and URL-encoded characters; query parameters belong in the URL, never in the params argument. Do not decode or re-encode.
  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/webhooks-security](https://www.twilio.com/docs/usage/webhooks/webhooks-security): "use the exact URL from Twilio including any URL-encoded characters. If you decode or re-encode the URL, signature validation fails."
- **Url port rules:** HTTP SMS and voice callbacks and HTTPS SMS callbacks: username/password dropped, port kept. HTTPS voice callbacks: username/password dropped and port also dropped before signing.
  Read 2026-10-20 from [www.twilio.com/docs/usage/security](https://www.twilio.com/docs/usage/security): "For voice callbacks over HTTPS: Twilio will drop the username and password (if any) from the URL before computing the signature. Twilio will also drop the port (if any)"
- **Url trailing slash:** A framework or server rewriting /twilio to /twilio/ gives a wrong hash because Twilio signed the URL without the trailing slash. For voice WSS handshakes, try appending a trailing / to the URL passed to the validator.
  Read 2026-10-20 from [www.twilio.com/docs/usage/security](https://www.twilio.com/docs/usage/security): "try appending a trailing / character to the URL that you pass to the signature validation method."
- **Sdk recommendation:** Twilio recommends the SDK validator and says not to implement your own
  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/webhooks-security](https://www.twilio.com/docs/usage/webhooks/webhooks-security): "Twilio recommends using the provided signature validation library from a Twilio SDK. Don't implement your own signature validation."
- **Published json example:**

  ```json
  {
    "note": "Page prints a JSON example but not the auth token, so the signature cannot be reproduced. The bodySHA256 in the URL does match SHA-256 of the printed body (verified locally).",
    "url": "https://example.com/myapp?bodySHA256=5ccde7145dfb8f56479710896586cb9d5911809d83afbe34627818790db0aec9",
    "body": "{\"CallSid\":\"CA1234567890ABCDE\",\"Caller\":\"+12349013030\"}",
    "signature": "hqeF3G9Hrnv6/R0jOhoYDD2PPUs="
  }
  ```

  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/webhooks-security](https://www.twilio.com/docs/usage/webhooks/webhooks-security): "const body = '{"CallSid":"CA1234567890ABCDE","Caller":"+12349013030"}'"
- **Official helper (Node.js):** twilio.validateRequest(authToken, twilioSignature, url, params) for form bodies; validateRequestWithBody(authToken, twilioSignature, url, body) for JSON (the page's samples call both on the client object from require('twilio'))
  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/webhooks-security](https://www.twilio.com/docs/usage/webhooks/webhooks-security): "client.validateRequest(authToken, twilioSignature, url, params)"
- **Official helper (Python):** from twilio.request_validator import RequestValidator; validator = RequestValidator(auth_token); validator.validate(url, params, twilio_signature). For JSON bodies the page shows validator.validate(url, body, twilio_signature).
  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/webhooks-security](https://www.twilio.com/docs/usage/webhooks/webhooks-security): "from twilio.request_validator import RequestValidator"
- **Official helper (.NET):** using Twilio.Security; var validator = new RequestValidator(authToken); validator.Validate(url, parameters, twilioSignature). For JSON bodies: validator.Validate(url, body, twilioSignature).
  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/webhooks-security](https://www.twilio.com/docs/usage/webhooks/webhooks-security): "using Twilio.Security;"
- **Published example:**

  ```json
  {
    "note": "From the Explore the algorithm yourself example (form-encoded POST). Verified by recomputing HMAC-SHA1 and Base64 locally: output equals the expected signature.",
    "auth_token": "12345",
    "url": "https://example.com/myapp.php?foo=1&bar=2",
    "post_params": "Digits=1234, To=+18005551212, From=+14158675310, Caller=+14158675310, CallSid=CA1234567890ABCDE",
    "string_to_sign": "https://example.com/myapp.php?foo=1&bar=2CallSidCA1234567890ABCDECaller+14158675310Digits1234From+14158675310To+18005551212",
    "signature": "L/OH5YylLD5NRKLltdqwSvS0BnU="
  }
  ```

  Read 2026-10-20 from [www.twilio.com/docs/usage/security](https://www.twilio.com/docs/usage/security): "Suppose your AuthToken is 12345."

## Delivery

- **Method and content type:** Inbound SMS: HTTP POST, application/x-www-form-urlencoded. Voice: GET or POST expecting TwiML. JSON payloads with application/json also exist for some webhooks.
  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/webhooks-faq](https://www.twilio.com/docs/usage/webhooks/webhooks-faq): "For inbound text messages, Twilio will send an HTTP POST request to your server with a body that uses the application/x-www-form-urlencoded encoding."
- **Event name:** Varies by product. For messaging status callbacks the MessageStatus form parameter carries the status; there is no single event-type header.
  Read 2026-10-20 from [www.twilio.com/docs/messaging/guides/track-outbound-message-status](https://www.twilio.com/docs/messaging/guides/track-outbound-message-status): "MessageStatus The status of the Message resource at the time the status callback request was sent."
- **Delivery or event id:** No single dedupe ID. Resource SIDs are in the body (for example MessageSid, CallSid). The connection-override retry path adds header I-Twilio-Idempotency-Token to distinguish retry attempts.
  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/webhooks-connection-overrides](https://www.twilio.com/docs/usage/webhooks/webhooks-connection-overrides): "To distinguish retry attempts, use the HTTP header I-Twilio-Idempotency-Token."
- **Handshake:** not stated by the provider
  Checked 2026-10-20 at [www.twilio.com/docs/usage/webhooks/webhooks-overview](https://www.twilio.com/docs/usage/webhooks/webhooks-overview).
- **Events per request:** not stated by the provider
  Checked 2026-10-20 at [www.twilio.com/docs/usage/webhooks/webhooks-overview](https://www.twilio.com/docs/usage/webhooks/webhooks-overview).
- **Parameter evolution:** Parameters vary by channel and event type and Twilio adds new ones without notice; validation must use all received parameters.
  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/webhooks-security](https://www.twilio.com/docs/usage/webhooks/webhooks-security): "Twilio occasionally adds parameters without advance notice."

## Responding and retries

- **Expected response:** Informational webhooks need a standard HTTP 200 OK. Webhooks that ask for instructions (inbound SMS, voice) expect a TwiML response (some require JSON).
  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/getting-started-twilio-webhooks](https://www.twilio.com/docs/usage/webhooks/getting-started-twilio-webhooks): "Informational Twilio webhooks require a standard HTTP 200 OK response. This shows that your web app received the webhook."
- **Response deadline:** Defaults: connect timeout 5000 ms, read timeout 15000 ms, total time 15000 ms. Voice call-related requests have a hard upper limit of 15 seconds.
  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/webhooks-connection-overrides](https://www.twilio.com/docs/usage/webhooks/webhooks-connection-overrides): "Twilio imposes a hard upper timeout of 15 seconds on all call-related HTTP requests."
- **Retries:** Default is one retry (rc=1) and the default retry policy (rp=ct) retries only on TCP connect or TLS handshake failure. 4xx, 5xx and read timeout (rt) retries must be opted in via the rp override. Twilio does not retry partial responses.
  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/webhooks-connection-overrides](https://www.twilio.com/docs/usage/webhooks/webhooks-connection-overrides): "ct retries on TCP connect or TLS handshake failure."
- **Disabling after failures:** not stated by the provider
  Checked 2026-10-20 at [www.twilio.com/docs/usage/webhooks/webhooks-overview](https://www.twilio.com/docs/usage/webhooks/webhooks-overview).
- **Ordering:** No ordering guarantee for status callbacks
  Read 2026-10-20 from [www.twilio.com/docs/messaging/guides/track-outbound-message-status](https://www.twilio.com/docs/messaging/guides/track-outbound-message-status): "there is no guarantee that the status callback requests always arrive at your endpoint in the order they were sent."
- **Duplicates:** not stated by the provider as a guarantee. A retried request carries the I-Twilio-Idempotency-Token header.
  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/webhooks-connection-overrides](https://www.twilio.com/docs/usage/webhooks/webhooks-connection-overrides): "To distinguish retry attempts, use the HTTP header I-Twilio-Idempotency-Token."
- **Twiml expectation:** Inbound SMS and voice webhooks respond with TwiML for the product
  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/webhooks-faq](https://www.twilio.com/docs/usage/webhooks/webhooks-faq): "If you are receiving a webhook for an inbound text message, your application would respond with TwiML for Programmable SMS."
- **Override parameters:** Overrides go in the URL fragment: ct (connect timeout ms, 100-10000, default 5000), rt (read timeout ms, 100-15000, default 15000), tt (total ms, 100-15000, default 15000), rc (retry count 0-5, default 1), rp (retry policy: 4xx, 5xx, ct, rt, all; default ct), sni (y/n, default y), e (edge, default ashburn). Example: https://example.com/foo#ct=500&rt=1000&tt=15000&rc=2&rp=4xx,5xx,ct,rt&sni=y&e=dublin,sydney. Documented as the legacy approach.
  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/webhooks-connection-overrides](https://www.twilio.com/docs/usage/webhooks/webhooks-connection-overrides): "https://example.com/foo#ct=500&rt=1000&tt=15000&rc=2&rp=4xx,5xx,ct,rt&sni=y&e=dublin,sydney"
- **Retry count default:** 1 (range 0 to 5)
  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/webhooks-connection-overrides](https://www.twilio.com/docs/usage/webhooks/webhooks-connection-overrides): "The number of attempts Twilio makes to retry the webhook should it fail."
- **Configuration api:** The Webhooks configuration API can set timeouts, retries and edge zones as webhook rules; Twilio recommends it over URL overrides. Its default retry behaviour is not stated on the pages read.
  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/webhooks-overview](https://www.twilio.com/docs/usage/webhooks/webhooks-overview): "Set the timeouts, retries, and edge zones Twilio uses and can collect as webhook rules."

## Events

Full list: https://www.twilio.com/docs/messaging/api/message-resource#message-status-values

Note: Twilio has no single event catalogue: each product sends its own webhooks. These are the Messaging status values sent to a StatusCallback URL, plus the inbound message status.

- **`queued`:** Outbound API request accepted and message queued
  Read 2026-10-20 from [www.twilio.com/docs/messaging/api/message-resource](https://www.twilio.com/docs/messaging/api/message-resource): "The API request to send an outbound message was successful and the message is queued to be sent out by a specific From sender."
- **`sent`:** Nearest upstream carrier accepted the outbound message
  Read 2026-10-20 from [www.twilio.com/docs/messaging/api/message-resource](https://www.twilio.com/docs/messaging/api/message-resource): "The nearest upstream carrier accepted the outbound message."
- **`delivered`:** Carrier (and where available the handset) confirmed delivery
  Read 2026-10-20 from [www.twilio.com/docs/messaging/api/message-resource](https://www.twilio.com/docs/messaging/api/message-resource): "Twilio has received confirmation of outbound message delivery from the upstream carrier"
- **`undelivered`:** Delivery receipt says the message was not delivered; ErrorCode set
  Read 2026-10-20 from [www.twilio.com/docs/messaging/api/message-resource](https://www.twilio.com/docs/messaging/api/message-resource): "Twilio received a delivery receipt indicating that the outbound message was not delivered."
- **`failed`:** Message failed to send; ErrorCode set
  Read 2026-10-20 from [www.twilio.com/docs/messaging/api/message-resource](https://www.twilio.com/docs/messaging/api/message-resource): "The outbound message failed to send."
- **`read`:** RCS and WhatsApp only: recipient opened the message
  Read 2026-10-20 from [www.twilio.com/docs/messaging/api/message-resource](https://www.twilio.com/docs/messaging/api/message-resource): "Channels supported: RCS and WhatsApp. The recipient opened the outbound message."
- **`received`:** Inbound message received and processing complete (inbound message webhook)
  Read 2026-10-20 from [www.twilio.com/docs/messaging/api/message-resource](https://www.twilio.com/docs/messaging/api/message-resource): "The inbound message was received and processing is complete."

## Setup and testing

- **Where the URL goes:** Product-specific: Console phone number or app configuration, or API parameters named callback or statusCallback (StatusCallback for messages). Webhooks configuration API manages delivery rules by URL.
  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/getting-started-twilio-webhooks](https://www.twilio.com/docs/usage/webhooks/getting-started-twilio-webhooks): "The typical API request parameter for the webhook URL gets named callback or statusCallback."
- **Test tools:** Console Debugger lists errors Twilio hits sending webhooks; Request Inspector on each Voice call record; the Webhooks configuration API has a Test webhook delivery page
  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/webhooks-faq](https://www.twilio.com/docs/usage/webhooks/webhooks-faq): "The Debugger will list any errors that Twilio finds when it sends a webhook to your application."
- **Source IP addresses:** No fixed range
  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/webhooks-security](https://www.twilio.com/docs/usage/webhooks/webhooks-security): "Twilio not having a fixed range of IP addresses that issue webhooks."
- **Status callback:** For Twilio to send status callbacks for a message you must provide the StatusCallback URL on each message to track (or configure at Messaging Service level)
  Read 2026-10-20 from [www.twilio.com/docs/messaging/guides/track-outbound-message-status](https://www.twilio.com/docs/messaging/guides/track-outbound-message-status): "you need to provide your status callback URL in the StatusCallback parameter of each message for which you want to track the MessageStatus."

## Pitfalls the provider warns about

- **1:** Twilio will not connect to an HTTPS URL with a self-signed certificate.
  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/webhooks-security](https://www.twilio.com/docs/usage/webhooks/webhooks-security): "Twilio won't connect to an HTTPS URL with a self-signed certificate."
- **2:** Behind a proxy the URL you reconstruct must equal the public URL configured in Twilio (scheme, host, port rules, trailing slash, encoding).
  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/webhooks-security](https://www.twilio.com/docs/usage/webhooks/webhooks-security): "When making a webhook request, use the exact URL from Twilio including any URL-encoded characters."
- **3:** For JSON requests do not use JSON properties as the validator's POST parameters.
  Read 2026-10-20 from [www.twilio.com/docs/usage/security](https://www.twilio.com/docs/usage/security): "don't use the JSON body to fill in the validator's parameter for POST parameters."
- **4:** Message status callbacks may arrive out of order.
  Read 2026-10-20 from [www.twilio.com/docs/messaging/guides/track-outbound-message-status](https://www.twilio.com/docs/messaging/guides/track-outbound-message-status): "there is no guarantee that the status callback requests always arrive at your endpoint in the order they were sent."
- **5:** Hidden whitespace in a body built for Twilio (for example in Studio HTTP Request) can break signature matching.
  Read 2026-10-20 from [www.twilio.com/docs/usage/security](https://www.twilio.com/docs/usage/security): "ensure that no hidden whitespaces are in the body."
- **6:** Voice call-related requests hard-cap at 15 seconds regardless of overrides.
  Read 2026-10-20 from [www.twilio.com/docs/usage/webhooks/webhooks-connection-overrides](https://www.twilio.com/docs/usage/webhooks/webhooks-connection-overrides): "This hard limit overrides any other overrides on call-processing requests for a good end-user calling experience."

## Conflicting or product-specific rules

- **Which port is signed:** One page states two rules: HTTPS SMS callbacks keep the port in the signed URL, HTTPS voice callbacks drop it. A receiver verifying both must know which product sent the request.
  - Read 2026-10-20 from https://www.twilio.com/docs/usage/security: "For SMS callbacks over HTTPS: Twilio will drop the username and password (if any) from the URL before computing the signature. Twilio will keep the port (if any)"
  - Read 2026-10-20 from https://www.twilio.com/docs/usage/security: "For voice callbacks over HTTPS: Twilio will drop the username and password (if any) from the URL before computing the signature. Twilio will also drop the port (if any)"

## In WebhookVault

What WebhookVault does with Twilio requests, read from its provider catalogue on 2026-10-20. These are facts about WebhookVault, not about Twilio.

- **Signature header it reads:** `X-Twilio-Signature`
- **Checks the signature:** yes (HMAC-SHA1 base64 over the public URL plus the sorted form parameters)
- **Secret field label:** Auth token
- **Where it finds the event name:** nowhere fixed; requests are listed without an event name
- **Where the capture URL goes in Twilio:** Console > Phone Numbers > Manage > Active numbers > your number > Messaging configuration > A message comes in
