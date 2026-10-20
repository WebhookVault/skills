# Paddle webhook facts

Generated from `data/providers/paddle.json` by `tools/provider-facts.mjs`; change the data and regenerate, never this file.
Every fact was read from Paddle's own pages on the date shown, with the sentence it came from. Quotes are verbatim except that long dashes are written as hyphens. "not stated by the provider" means the pages read did not say; it does not mean there is no rule.

## Contents

- [Signature](#signature)
- [Delivery](#delivery)
- [Responding and retries](#responding-and-retries)
- [Events](#events)
- [Setup and testing](#setup-and-testing)
- [Pitfalls the provider warns about](#pitfalls-the-provider-warns-about)
- [In WebhookVault](#in-webhookvault)

## Signature

- **Signature header:** Paddle-Signature
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/signature-verification](https://developer.paddle.com/webhooks/about/signature-verification): "All webhooks sent by Paddle include a `Paddle-Signature` header."
- **Scheme:** HMAC-SHA256 with the destination's endpoint secret key string used as-is as the key (UTF-8 bytes of the whole string, including its pdl_ prefix; no base64 decoding); h1 is the lowercase hex digest. The prose does not name the encoding; the manual Node example uses .digest('hex') and the manual C# example uses new HMACSHA256(Encoding.UTF8.GetBytes(secretKey)).
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/signature-verification](https://developer.paddle.com/webhooks/about/signature-verification): "const hashedPayload = createHmac("sha256", secretKey) .update(signedPayload, "utf8") .digest("hex");"
- **Signed content:** the ts value, a colon, then the raw request body: ts:body
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/signature-verification](https://developer.paddle.com/webhooks/about/signature-verification): "The extracted timestamp (`ts`) + A colon (`:`) + The raw body of the request"
- **Header format:** semicolon-separated key=value pairs: ts=<unix seconds>;h1=<signature>. Always at least one h1; during secret rotation more than one h1 is returned.
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/signature-verification](https://developer.paddle.com/webhooks/about/signature-verification): "ts=1671552777;h1=eb4d0dc8853be92b7f063b9f3ba5233eb920a09459b6e6b2c26705b4364db151"
- **Where the secret comes from:** Dashboard: Paddle > Events > Notifications, edit the destination, copy the secret key field. API: GET /notification-settings/{notification_setting_id} returns endpoint_secret_key (example value looks like pdl_ntfset_..._<random>).
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/signature-verification](https://developer.paddle.com/webhooks/about/signature-verification): "Send a GET request to the `/notification-settings/{notification_setting_id}` endpoint. If successful, Paddle returns the notification destination settings, including the `endpoint_secret_key`."
- **Secret scope:** per notification destination (so per endpoint; sandbox and live accounts are separate)
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/signature-verification](https://developer.paddle.com/webhooks/about/signature-verification): "Paddle generates a secret key for each notification destination that you create."
- **Timestamp tolerance:** Docs recommend checking ts against the current time and rejecting events that are too old. They state the SDK helper default tolerance is five seconds. No tolerance is stated for manual verification beyond 'may like to check' and 'too old'.
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/signature-verification](https://developer.paddle.com/webhooks/about/signature-verification): "our SDK helper methods check the timestamp (`ts`) against the current time and reject events that are too old. The default tolerance between the timestamp and the current time is five seconds."
- **Secret rotation:** During rotation Paddle sends more than one h1 in the header. Receivers should accept if any h1 matches (the docs say 'more than one h1 is returned'; they do not spell out the accept-any rule). Wording 'We may add support for secret rotation in the future' suggests the feature is not fully described; grace period length not stated.
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/signature-verification](https://developer.paddle.com/webhooks/about/signature-verification): "During secret rotation, more than one `h1` is returned while secrets are rotated out."
- **Raw body:** Do not transform the raw body at all (no whitespace or other formatting changes), or signatures will not match.
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/signature-verification](https://developer.paddle.com/webhooks/about/signature-verification): "Don't transform or process the raw body of the request, including adding whitespace or applying other formatting."
- **Header parts quote:** ts: Unix timestamp. h1: event signature; at least one, more than one during rotation.
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/signature-verification](https://developer.paddle.com/webhooks/about/signature-verification): "Signatures contain at least one `h1`. We may add support for secret rotation in the future. During secret rotation, more than one `h1` is returned while secrets are rotated out."
- **Example header only:** The docs print an example Paddle-Signature header but no secret or body, so it is NOT a usable test vector.
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/signature-verification](https://developer.paddle.com/webhooks/about/signature-verification): "ts=1671552777;h1=eb4d0dc8853be92b7f063b9f3ba5233eb920a09459b6e6b2c26705b4364db151"
- **Official helper (Node.js):** await paddle.webhooks.unmarshal(rawRequestBody, secretKey, signature) (package @paddle/paddle-node-sdk; rawRequestBody is the body as a string, signature is the paddle-signature header; returns the event entity, throws on mismatch)
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/signature-verification](https://developer.paddle.com/webhooks/about/signature-verification): "const eventData = await paddle.webhooks.unmarshal( rawRequestBody, secretKey, signature, );"
- **Official helper (Python):** from paddle_billing.Notifications import Secret, Verifier; integrity_check = Verifier().verify(request, Secret('WEBHOOK_SECRET_KEY'))
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/signature-verification](https://developer.paddle.com/webhooks/about/signature-verification): "integrity_check = Verifier().verify(request, Secret('WEBHOOK_SECRET_KEY'))"
- **Official helper (.NET):** no official .NET SDK helper shown (the SDK tabs cover Go, Node.js, PHP and Python). The docs do give a manual C# example (HMACSHA256 over ts:body, key = UTF-8 bytes of the secret string).
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/signature-verification](https://developer.paddle.com/webhooks/about/signature-verification): "using var hmac = new HMACSHA256(Encoding.UTF8.GetBytes(secretKey));"
- **Official helper (Go):** paddle.NewWebhookVerifier(secret) then verifier.Verify(req) or verifier.Middleware(handler)
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/signature-verification](https://developer.paddle.com/webhooks/about/signature-verification): "webhookVerifier := paddle.NewWebhookVerifier(os.Getenv("WEBHOOK_SECRET_KEY"))"
- **Official helper (Php):** (new Verifier())->verify($request, new Secret('WEBHOOK_SECRET_KEY')) with Paddle\SDK\Notifications
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/signature-verification](https://developer.paddle.com/webhooks/about/signature-verification): "(new Verifier())->verify( $request, new Secret('WEBHOOK_SECRET_KEY') );"

## Delivery

- **Method and content type:** HTTPS POST with a JSON payload. Content-Type header value not stated. User agent string is 'Paddle' (docs advise matching it in firewall rules).
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/respond-to-webhooks](https://developer.paddle.com/webhooks/about/respond-to-webhooks): "Can accept `POST` requests with a JSON payload"
- **Event name:** top-level JSON field event_type, format entity.action (for example customer.created)
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/how-webhooks-work](https://developer.paddle.com/webhooks/about/how-webhooks-work): "`event_type` | The type of event, in the format `entity.action` (for example, `customer.created`)."
- **Delivery or event id:** event_id (evt_ prefix) is the dedupe key and is the same across retries and across destinations; notification_id (ntf_ prefix) identifies the delivery to one destination. The page describes notification_id as 'for this delivery attempt' yet also says one notification is retried, so treat event_id as the dedupe key as Paddle instructs.
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/how-webhooks-work](https://developer.paddle.com/webhooks/about/how-webhooks-work): "`event_id` | Unique ID for this event, prefixed with `evt_`. Use this to deduplicate events you may receive more than once."
- **Handshake:** not stated by the provider (no challenge or ping on setup)
  Checked 2026-10-20 at [developer.paddle.com/webhooks/about/notification-destinations](https://developer.paddle.com/webhooks/about/notification-destinations).
- **Events per request:** one event per request: every webhook has the same top-level structure (event_id, event_type, occurred_at, notification_id, data)
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/how-webhooks-work](https://developer.paddle.com/webhooks/about/how-webhooks-work): "Every webhook Paddle sends has the same top-level structure, regardless of the event type"
- **Notification id quote:** notification_id: unique ID prefixed ntf_; a single event can produce multiple notifications (one per destination)
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/how-webhooks-work](https://developer.paddle.com/webhooks/about/how-webhooks-work): "Each notification has its own `notification_id` but they share the same `event_id`."

## Responding and retries

- **Expected response:** HTTP 200. Any other status code is treated as failure and retried.
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/respond-to-webhooks](https://developer.paddle.com/webhooks/about/respond-to-webhooks): "If your server sends another kind of status code or doesn't respond within five seconds, Paddle automatically retries"
- **Response deadline:** five seconds; respond before doing any internal processing
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/respond-to-webhooks](https://developer.paddle.com/webhooks/about/respond-to-webhooks): "should respond with an HTTP `200` status code **within five seconds**."
- **Retries:** Live accounts: up to 60 attempts over about two days (around 10 in the first hour, around 45 in the first day); wait before the next attempt is 60 x n^1.1 seconds where n is attempts made so far (table: attempt 2 after 1m, attempt 3 after 2m 9s, attempt 60 after 1h 28m, 1d 18h since first). Sandbox accounts: 3 attempts in total, within about two minutes (20s, then 43s). Times approximate; an attempt can be up to a minute later.
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/respond-to-webhooks](https://developer.paddle.com/webhooks/about/respond-to-webhooks): "For sandbox accounts, we make 3 attempts in total, all within about two minutes. For live accounts, we make up to 60 attempts in total over about two days."
- **Disabling after failures:** not stated by the provider (docs say a notification whose attempts are exhausted gets status failed and can be replayed via the API; they do not describe Paddle deactivating the destination)
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/respond-to-webhooks](https://developer.paddle.com/webhooks/about/respond-to-webhooks): "When all attempts to deliver a webhook are exhausted, its status is set to `failed`."
- **Ordering:** Order not guaranteed; store and check occurred_at before making changes.
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/respond-to-webhooks](https://developer.paddle.com/webhooks/about/respond-to-webhooks): "We can't guarantee the order of delivery for webhooks. They may be delivered in a different order to the order they're generated. Store and check the `occurred_at` date against a webhook before making changes."
- **Duplicates:** At-least-once delivery; make processing idempotent, dedupe on event_id.
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/how-webhooks-work](https://developer.paddle.com/webhooks/about/how-webhooks-work): "Paddle guarantees **at-least-once delivery**."

## Events

Full list: https://developer.paddle.com/llms/webhooks.txt

Note: https://developer.paddle.com/llms/webhooks.txt (each event has its own page under developer.paddle.com/webhooks/<group>/<event>)

- **Checkout sequence:** typical order: transaction.created, customer.created, address.created, business.created (optional), transaction.paid, subscription.created (if recurring), transaction.completed
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/how-webhooks-work](https://developer.paddle.com/webhooks/about/how-webhooks-work): "For a subscription, `transaction.paid` is the earliest point at which you can be sure payment has been captured."

- **`subscription.created`:** a subscription record was created (checkout of a recurring item)
  Read 2026-10-20 from [developer.paddle.com/llms/webhooks.txt](https://developer.paddle.com/llms/webhooks.txt): "Occurs when a subscription is created."
- **`subscription.activated`:** subscription became active (first payment succeeded)
  Read 2026-10-20 from [developer.paddle.com/llms/webhooks.txt](https://developer.paddle.com/llms/webhooks.txt): "Occurs when a subscription becomes active."
- **`subscription.updated`:** any change to a subscription (items, scheduled change, billing details)
  Read 2026-10-20 from [developer.paddle.com/llms/webhooks.txt](https://developer.paddle.com/llms/webhooks.txt): "Occurs when a subscription is updated."
- **`subscription.canceled`:** subscription canceled
  Read 2026-10-20 from [developer.paddle.com/llms/webhooks.txt](https://developer.paddle.com/llms/webhooks.txt): "Occurs when a subscription is canceled."
- **`subscription.past_due`:** a renewal transaction is unpaid; status becomes past_due
  Read 2026-10-20 from [developer.paddle.com/llms/webhooks.txt](https://developer.paddle.com/llms/webhooks.txt): "Occurs when a subscription has an unpaid transaction. Its `status` changes to `past_due`."
- **`transaction.paid`:** payment captured; earliest point you can be sure payment succeeded
  Read 2026-10-20 from [developer.paddle.com/llms/webhooks.txt](https://developer.paddle.com/llms/webhooks.txt): "Occurs when a transaction is paid. Its status field changes to `paid`."
- **`transaction.completed`:** Paddle finished all internal processing of the transaction
  Read 2026-10-20 from [developer.paddle.com/llms/webhooks.txt](https://developer.paddle.com/llms/webhooks.txt): "Occurs when a transaction is completed. Its status field changes to `completed`."
- **`transaction.payment_failed`:** a payment attempt on a transaction failed
  Read 2026-10-20 from [developer.paddle.com/llms/webhooks.txt](https://developer.paddle.com/llms/webhooks.txt): "Occurs when a payment fails for a transaction."
- **`customer.created`:** a customer record was created
  Read 2026-10-20 from [developer.paddle.com/llms/webhooks.txt](https://developer.paddle.com/llms/webhooks.txt): "Occurs when a customer is created."
- **`adjustment.created`:** a refund, credit or chargeback adjustment was created
  Read 2026-10-20 from [developer.paddle.com/llms/webhooks.txt](https://developer.paddle.com/llms/webhooks.txt): "Occurs when an adjustment is created."

## Setup and testing

- **Where the URL goes:** Dashboard: Paddle > Events > Notifications > New destination (description, type webhook or email, URL, API version, usage type, events); or the create notification setting API. Max 10 active destinations.
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/notification-destinations](https://developer.paddle.com/webhooks/about/notification-destinations): "You can create as many notification destinations as you want, but only 10 can be active at once."
- **Test tools:** Webhook simulator (Paddle > Events > Simulations, or POST /simulations): single events or scenarios; destination usage type (traffic_source) must be 'all' (Platform and simulation) or 'simulation'; platform-only destinations receive real events only. Sandbox accounts also exist. Failed notifications can be replayed through the replay notification API.
  Read 2026-10-20 from [developer.paddle.com/webhooks/simulator/test-webhooks](https://developer.paddle.com/webhooks/simulator/test-webhooks): "Only destinations with the **Usage type** (`traffic_source`) of **Platform and simulation** (`all`) or **Simulation** (`simulation`) work with webhook simulator."
- **Source IP addresses:**

  ```json
  {
    "sandbox": [
      "34.194.127.46",
      "54.234.237.108",
      "3.208.120.145",
      "44.226.236.210",
      "44.241.183.62",
      "100.20.172.113"
    ],
    "live": [
      "34.232.58.13",
      "34.195.105.136",
      "34.237.3.244",
      "35.155.119.135",
      "52.11.166.252",
      "34.212.5.7"
    ]
  }
  ```

  Read 2026-10-20 from [developer.paddle.com/webhooks/about/respond-to-webhooks](https://developer.paddle.com/webhooks/about/respond-to-webhooks): "We recommend adding Paddle webhook IP addresses to your allowlist, and rejecting webhooks that come from other sources."

Notes from reading these pages (our words, not the provider's):

- The manual Ruby example on the signature page rejects events older than 5 seconds (current_time - event_time > 5), consistent with the five-second statement.
- The 5 second SDK tolerance appears twice on the signature page (SDK info callout and manual step 2); both say five seconds.

## Pitfalls the provider warns about

- **1:** Respond 200 before doing any internal processing; queue events and process asynchronously.
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/respond-to-webhooks](https://developer.paddle.com/webhooks/about/respond-to-webhooks): "You should respond before doing any internal processing."
- **2:** Serverless cold starts can cause intermittent five-second timeouts; consider pre-warming.
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/respond-to-webhooks](https://developer.paddle.com/webhooks/about/respond-to-webhooks): "consider pre-warming your function to prevent cold starts that might cause intermittent timeouts."
- **3:** A WAF may incorrectly block Paddle; bypass bot checks on the webhook path, restrict by Paddle IPs and user agent 'Paddle'.
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/respond-to-webhooks](https://developer.paddle.com/webhooks/about/respond-to-webhooks): "requests from Paddle may be blocked incorrectly."
- **4:** Sandbox and live use different IP lists and have different retry schedules (3 attempts vs up to 60).
  Read 2026-10-20 from [developer.paddle.com/webhooks/about/respond-to-webhooks](https://developer.paddle.com/webhooks/about/respond-to-webhooks): "Allow different IP addresses for `sandbox` and `live` accounts:"
- **5:** Platform-type destinations never receive simulated events.
  Read 2026-10-20 from [developer.paddle.com/webhooks/simulator/test-webhooks](https://developer.paddle.com/webhooks/simulator/test-webhooks): "Platform destinations can only receive traffic for real events to avoid sending simulated data to production endpoints."

Pages that could not be read when these facts were taken:

- https://developer.paddle.com/webhooks/overview: 404 in markdown form; the event index was read from developer.paddle.com/llms/webhooks.txt instead; full_list_url points to the working index

## In WebhookVault

What WebhookVault does with Paddle requests, read from its provider catalogue on 2026-10-20. These are facts about WebhookVault, not about Paddle.

- **Signature header it reads:** `Paddle-Signature`
- **Checks the signature:** yes (HMAC-SHA256 hex over "ts:body" from the ts and h1 values, 5 minute tolerance)
- **Secret field label:** Signing secret
- **Where it finds the event name:** body `event_type`
- **Where the capture URL goes in Paddle:** Paddle > Developer tools > Notifications > New destination
