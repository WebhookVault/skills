# Shopify webhook facts

Generated from `data/providers/shopify.json` by `tools/provider-facts.mjs`; change the data and regenerate, never this file.
Every fact was read from Shopify's own pages on the date shown, with the sentence it came from. Quotes are verbatim except that long dashes are written as hyphens. "not stated by the provider" means the pages read did not say; it does not mean there is no rule.

## Contents

- [Signature](#signature)
- [Delivery](#delivery)
- [Responding and retries](#responding-and-retries)
- [Events](#events)
- [Setup and testing](#setup-and-testing)
- [Compliance](#compliance)
- [Pitfalls the provider warns about](#pitfalls-the-provider-warns-about)
- [Conflicting or product-specific rules](#conflicting-or-product-specific-rules)
- [In WebhookVault](#in-webhookvault)

## Signature

- **Signature header:** X-Shopify-Hmac-Sha256 (written X-Shopify-Hmac-SHA256 on the verify page; header names are case-insensitive, HTTP/2 often lowercases them). HTTPS deliveries only.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/delivery-structure](https://shopify.dev/docs/apps/build/webhooks/delivery-structure): "Base64-encoded HMAC signature for verifying the delivery came from Shopify. HTTPS only."
- **Scheme:** HMAC-SHA256, base64 encoded, keyed with the app client secret.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/verify-deliveries](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries): "compute HMAC-SHA256 of the raw request body using your app's client secret as the key, then compare it to the decoded header value."
- **Signed content:** The raw request body only (no timestamp or id is part of the signed content).
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/verify-deliveries](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries): "generated using your app's client secret and the raw request body."
- **Header format:** A single base64 string, no prefix or key=value pairs. The docs example decodes both the computed digest and the header from base64 before comparing with crypto.timingSafeEqual.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/verify-deliveries](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries): "crypto.timingSafeEqual(Buffer.from(calculatedHmacDigest, 'base64'), Buffer.from(shopifyHmac, 'base64'))"
- **Where the secret comes from:** The app's client secret (the app credentials), not a per-subscription secret.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/verify-deliveries](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries): "generated using your app's client secret and the raw request body."
- **Secret scope:** Per app: one client secret signs every webhook the app receives, across all shops and topics.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/verify-deliveries](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries): "compute HMAC-SHA256 of the raw request body using your app's client secret as the key"
- **Timestamp tolerance:** not stated by the provider (the signature covers only the body; X-Shopify-Triggered-At exists but no replay window is described)
  Checked 2026-10-20 at [shopify.dev/docs/apps/build/webhooks/verify-deliveries](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries).
- **Secret rotation:** After rotating the app client secret, up to an hour may pass before digests use the new secret. Dual-signature behaviour is not described.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/verify-deliveries](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries): "If you rotate your app's client secret, it can take up to an hour for the HMAC digest to be generated using the new secret."
- **Raw body:** Capture the raw body before any body parser; place verification middleware before body parsing; ensure encoding is correct.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/verify-deliveries](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries): "HMAC verification requires the raw request body. If you're using a body parser middleware like express.json(), it parses the body before your verification code runs."
- **Header case:** Treat header names as case-insensitive.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/delivery-structure](https://shopify.dev/docs/apps/build/webhooks/delivery-structure): "Treat header names as case-insensitive in your code, as HTTP/2 often lowercases them."
- **Verify always:** Verify before trusting the payload; skip only in development with mock tools. Not required for Google Pub/Sub or Amazon EventBridge deliveries.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/verify-deliveries](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries): "Always verify HMAC before trusting payload contents."
- **Published test vector note:** The docs print only code, plus an example header value in the reference (X-Shopify-Hmac-Sha256: xT6yH5jZ...) with no secret or body; there is no complete worked example.
  Read 2026-10-20 from [shopify.dev/docs/api/webhooks/latest](https://shopify.dev/docs/api/webhooks/latest): "X-Shopify-Hmac-Sha256: xT6yH5jZfQm6Q3lC8nA0r7sV2bP9dK1eL4wG0hM5nYI="
- **Official helper (Node.js):** shopify.webhooks.validate({ rawBody: req.body, rawRequest: req, rawResponse: res }) returns { valid, topic, domain } (shopify-api library); React Router template: authenticate.webhook(request) from ../shopify.server verifies before the handler runs
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/verify-deliveries](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries): "const {valid, topic, domain} = await shopify.webhooks.validate({"
- **Official helper (Python):** not stated by the provider on the pages read
  Checked 2026-10-20 at [shopify.dev/docs/apps/build/webhooks/verify-deliveries](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries).
- **Official helper (.NET):** not stated by the provider on the pages read
  Checked 2026-10-20 at [shopify.dev/docs/apps/build/webhooks/verify-deliveries](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries).

## Delivery

- **Method and content type:** HTTP POST with a JSON payload; the reference example request shows Content-Type: application/json. Deliveries can also go to Google Pub/Sub or Amazon EventBridge instead of HTTPS.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/delivery-structure](https://shopify.dev/docs/apps/build/webhooks/delivery-structure): "For HTTPS destinations, Shopify sends an HTTP POST with a JSON payload in the request body and delivery metadata in HTTP headers."
- **Event name:** X-Shopify-Topic header (for example products/update). The body does not name the topic.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/delivery-structure](https://shopify.dev/docs/apps/build/webhooks/delivery-structure): "The topic name (for example, products/update)."
- **Delivery or event id:** X-Shopify-Webhook-Id identifies one delivery (dedupe on it). X-Shopify-Event-Id is shared by all deliveries produced by the same merchant action, so two subscriptions to one topic give different Webhook-Ids and the same Event-Id.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/delivery-structure](https://shopify.dev/docs/apps/build/webhooks/delivery-structure): "A unique composite key per delivery. Use to identify and deduplicate individual deliveries."
- **Handshake:** not stated by the provider (no challenge or ping on subscription)
  Checked 2026-10-20 at [shopify.dev/docs/apps/build/webhooks/subscribe](https://shopify.dev/docs/apps/build/webhooks/subscribe).
- **Events per request:** One delivery per qualifying change, with one JSON resource payload (no arrays described). include_fields can shrink the payload; identical small payloads in a short window are debounced (later one dropped).
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/delivery-structure](https://shopify.dev/docs/apps/build/webhooks/delivery-structure): "Each qualifying change sends a webhook delivery to the destination configured in your subscription's uri."
- **Content type example:** Example request headers include Content-Type: application/json.
  Read 2026-10-20 from [shopify.dev/docs/api/webhooks/latest](https://shopify.dev/docs/api/webhooks/latest): "Content-Type: application/json"
- **Event id:** X-Shopify-Event-Id: shared across deliveries from one merchant action.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/delivery-structure](https://shopify.dev/docs/apps/build/webhooks/delivery-structure): "A unique ID shared across all deliveries produced by the same merchant action."
- **Event id note:** Different Webhook-Id, same Event-Id for multiple subscriptions on one topic.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/verify-deliveries](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries): "Each has a different X-Shopify-Webhook-Id but shares the same X-Shopify-Event-Id."
- **Other headers:** X-Shopify-Shop-Domain (myshopify.com domain of the store), X-Shopify-API-Version (API version used to serialize the payload), X-Shopify-Triggered-At (timestamp of when Shopify triggered the delivery), X-Shopify-Name (optional, your subscription name).
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/delivery-structure](https://shopify.dev/docs/apps/build/webhooks/delivery-structure): "The API version used to serialize the payload."
- **Debouncing:** With include_fields, identical payloads close together can be dropped; include a field that always changes, such as updated_at.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/delivery-structure](https://shopify.dev/docs/apps/build/webhooks/delivery-structure): "Shopify debounces deliveries with identical payloads that arrive within a short time window, dropping the later one."
- **Api version header:** X-Shopify-API-Version on HTTPS deliveries; for Pub/Sub and EventBridge the version is in the message payload. Version for app-specific (TOML) subscriptions comes from webhooks.api_version; for shop-specific subscriptions from the request URL used to create them.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/subscribe](https://shopify.dev/docs/apps/build/webhooks/subscribe): "Each delivery includes the API version that serialized its payload."

## Responding and retries

- **Expected response:** A 200-range status. Anything outside 200-299, including 3xx redirects, is an error.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/verify-deliveries](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries): "Any response outside the 200 range, including 3XX codes, is treated as an error."
- **Response deadline:** 1 second connection timeout and 5 seconds for the whole request.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/verify-deliveries](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries): "Shopify has a one-second connection timeout and a five-second timeout for the entire request."
- **Retries:** 8 retries over the next 4 hours after no response or an error. The retry interval grows after each failure. After 8 failed attempts Shopify stops delivering that webhook.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/verify-deliveries](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries): "If Shopify receives no response or an error, it retries 8 times over the next 4 hours."
- **Disabling after failures:** After 8 consecutive failures the subscription is automatically deleted if it was configured through the Admin API (shop-specific). Warning emails go to the app's emergency developer email. App-specific subscriptions defined in shopify.app.toml are not deleted by Shopify on failure. Removed subscriptions get no deliveries until recreated.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/verify-deliveries](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries): "After 8 consecutive failures, the subscription is automatically deleted if it was configured using the Admin API."
- **Ordering:** Not guaranteed within a topic or across topics for the same resource (for example products/update can arrive before products/create). Use X-Shopify-Triggered-At or the payload updated_at to order.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks](https://shopify.dev/docs/apps/build/webhooks): "Shopify doesn't guarantee ordering within a topic, or across different topics for the same resource."
- **Duplicates:** Possible (for example after a network timeout or a retry). Make processing idempotent or store X-Shopify-Webhook-Id and skip seen ids, returning success.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/verify-deliveries](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries): "Shopify minimizes duplicate deliveries, but your app might receive the same webhook more than once"
- **Keep alive:** Shopify reuses connections; keep HTTP Keep-Alive enabled on the endpoint.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/verify-deliveries](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries): "Ensure Keep-Alive is enabled on your endpoint to reduce overhead from concurrent requests."
- **Retries interval:** Interval before the next retry increases each time.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/troubleshoot](https://shopify.dev/docs/apps/build/webhooks/troubleshoot): "Each time a delivery fails, the interval before the next retry increases."
- **Retries stop:** No delivery attempts after the 8th failure.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/troubleshoot](https://shopify.dev/docs/apps/build/webhooks/troubleshoot): "After 8 failed delivery attempts, Shopify stops attempting delivery."
- **Disabling app specific:** TOML-defined subscriptions survive failures; Admin API subscriptions are deleted.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/subscribe](https://shopify.dev/docs/apps/build/webhooks/subscribe): "Failing subscriptions will not be deleted by Shopify."
- **Disabling emails:** Warning emails to the emergency developer address.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/verify-deliveries](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries): "Warning emails are sent to the app's emergency developer email address."
- **Disabling recreate:** Fix the cause and recreate removed subscriptions.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/troubleshoot](https://shopify.dev/docs/apps/build/webhooks/troubleshoot): "Fix the issue, then recreate the webhook subscriptions."
- **Ordering timestamps:** Order with header or payload timestamps.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks](https://shopify.dev/docs/apps/build/webhooks): "Shopify recommends using timestamps provided in the header (X-Shopify-Triggered-At) or in the payload itself (updated_at) to organize webhooks."
- **Not guaranteed:** Delivery is not guaranteed; run reconciliation jobs (many GraphQL queries accept updated_at filters).
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks](https://shopify.dev/docs/apps/build/webhooks): "Webhook delivery isn't always guaranteed, and your app can miss or mishandle events for other reasons"
- **Delays:** Webhooks can arrive late (up to a day is mentioned); compare the webhook timestamp to the current time if that matters.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/troubleshoot](https://shopify.dev/docs/apps/build/webhooks/troubleshoot): "If receiving webhooks up to a day late might cause issues in your app, then compare the timestamp of the webhook to the current date and time."

## Events

Full list: https://shopify.dev/docs/api/webhooks

- **`orders/create`:** A new order was created in the shop.
  Read 2026-10-20 from [shopify.dev/docs/api/webhooks/latest](https://shopify.dev/docs/api/webhooks/latest): "orders/create: Sample Payload"
- **`orders/paid`:** An order was paid.
  Read 2026-10-20 from [shopify.dev/docs/api/webhooks/latest](https://shopify.dev/docs/api/webhooks/latest): "orders/paid: Sample Payload"
- **`orders/updated`:** An order changed.
  Read 2026-10-20 from [shopify.dev/docs/api/webhooks/latest](https://shopify.dev/docs/api/webhooks/latest): "orders/updated: Sample Payload"
- **`orders/cancelled`:** An order was cancelled.
  Read 2026-10-20 from [shopify.dev/docs/api/webhooks/latest](https://shopify.dev/docs/api/webhooks/latest): "orders/cancelled: Sample Payload"
- **`products/create`:** A new product was created.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/subscribe](https://shopify.dev/docs/apps/build/webhooks/subscribe): "products/update fires when an existing product changes; products/create fires when a new one is created."
- **`products/update`:** An existing product changed.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/subscribe](https://shopify.dev/docs/apps/build/webhooks/subscribe): "products/update fires when an existing product changes"
- **`refunds/create`:** A refund was created.
  Read 2026-10-20 from [shopify.dev/docs/api/webhooks/latest](https://shopify.dev/docs/api/webhooks/latest): "refunds/create: Sample Payload"
- **`customers/update`:** A customer record changed.
  Read 2026-10-20 from [shopify.dev/docs/api/webhooks/latest](https://shopify.dev/docs/api/webhooks/latest): "customers/update: Sample Payload"
- **`app/uninstalled`:** The app was uninstalled from a shop.
  Read 2026-10-20 from [shopify.dev/docs/api/webhooks/latest](https://shopify.dev/docs/api/webhooks/latest): "app/uninstalled: Sample Payload"
- **`customers/data_request`:** Mandatory compliance topic: a customer asked the merchant for their stored data.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/compliance/privacy-law-compliance](https://shopify.dev/docs/apps/build/compliance/privacy-law-compliance): "Requests to view stored customer data"
- **`customers/redact`:** Mandatory compliance topic: delete a customer's data.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/compliance/privacy-law-compliance](https://shopify.dev/docs/apps/build/compliance/privacy-law-compliance): "Requests to delete customer data"
- **`shop/redact`:** Mandatory compliance topic: delete a shop's data after uninstall.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/compliance/privacy-law-compliance](https://shopify.dev/docs/apps/build/compliance/privacy-law-compliance): "Requests to delete shop data"

## Setup and testing

- **Where the URL goes:** App-specific (recommended): [[webhooks.subscriptions]] in shopify.app.toml with topics and uri, plus [webhooks] api_version; released with 'shopify app deploy' or via Dev Dashboard Versions. Shop-specific: GraphQL Admin API webhookSubscriptionCreate. uri may be an HTTPS URL, a pubsub://project:topic URI or an EventBridge ARN.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/subscribe](https://shopify.dev/docs/apps/build/webhooks/subscribe): "uri | Delivery destination. HTTPS URL, AWS EventBridge ARN, or Google Pub/Sub URI."
- **Test tools:** 'shopify app webhook trigger --api-version=<version> --address=<destination> --topic=<topic-name>' sends a synthetic webhook to your endpoint; it does not test subscription configuration. Dev Dashboard shows delivery logs (7 days) and metrics.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/subscribe](https://shopify.dev/docs/apps/build/webhooks/subscribe): "shopify app webhook trigger --api-version=<version> --address=<destination> --topic=<topic-name>"
- **Source IP addresses:** not stated by the provider on the pages read
  Checked 2026-10-20 at [shopify.dev/docs/apps/build/webhooks/verify-deliveries](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries).
- **Recommended destination:** Shopify recommends Google Pub/Sub; HTTPS needs extra care.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/subscribe](https://shopify.dev/docs/apps/build/webhooks/subscribe): "Shopify recommends using Google Pub/Sub as a cloud-based solution for delivering webhooks."
- **Trigger limit:** The trigger does not exercise your real subscription.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/get-started](https://shopify.dev/docs/apps/build/webhooks/get-started): "It doesn't test your subscription configuration."
- **Logs window:** Delivery logs cover the past 7 days.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/troubleshoot](https://shopify.dev/docs/apps/build/webhooks/troubleshoot): "The Logs page shows individual deliveries filterable by topic, status, and destination shop over the past 7 days."
- **Versioning:** Webhooks are versioned like other Shopify APIs; Shopify recommends updating to the latest stable version each quarter; existing subscriptions keep their earlier version until you update and deploy.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/subscribe](https://shopify.dev/docs/apps/build/webhooks/subscribe): "Shopify recommends updating to the latest stable API version each quarter."

## Compliance

- **Mandatory topics:** customers/data_request; customers/redact; shop/redact
  Read 2026-10-20 from [shopify.dev/docs/apps/build/compliance/privacy-law-compliance](https://shopify.dev/docs/apps/build/compliance/privacy-law-compliance): "Every app that's distributed through the Shopify App Store must subscribe to the following compliance webhook topics:"
- **Scope:** Mandatory for apps distributed through the Shopify App Store (public apps); the docs example config comment elsewhere says public apps only. Apps are rejected in review without them.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/compliance/privacy-law-compliance](https://shopify.dev/docs/apps/build/compliance/privacy-law-compliance): "If you don't provide URLs for the mandatory compliance webhooks, or your app doesn't respond to these webhooks as required, then your app will be rejected"
- **Invalid hmac:** Respond 401 Unauthorized to an invalid HMAC on a compliance webhook.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/compliance/privacy-law-compliance](https://shopify.dev/docs/apps/build/compliance/privacy-law-compliance): "If a mandatory compliance webhook sends a request with an invalid Shopify HMAC header, then the app must return a 401 Unauthorized HTTP status."
- **Content type:** Compliance webhooks are POST with a JSON body and Content-Type application/json.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/compliance/privacy-law-compliance](https://shopify.dev/docs/apps/build/compliance/privacy-law-compliance): "The app must handle POST requests with a JSON body and Content-Type header set to application/json sent to mandatory compliance webhooks."
- **Response and deadline:** Answer with a 2xx to confirm receipt, then complete the action within 30 days (unless law requires you to retain the data, in which case do not complete a redaction).
  Read 2026-10-20 from [shopify.dev/docs/apps/build/compliance/privacy-law-compliance](https://shopify.dev/docs/apps/build/compliance/privacy-law-compliance): "Complete the action within 30 days of receiving the request."
- **Shop redact timing:** shop/redact is sent 48 hours after uninstall.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/compliance/privacy-law-compliance](https://shopify.dev/docs/apps/build/compliance/privacy-law-compliance): "48 hours after a store owner uninstalls your app, Shopify sends a payload on the shop/redact topic."
- **Customers redact timing:** customers/redact is delayed: 10 days after the request if the customer has no order in six months, otherwise withheld until six months have passed.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/compliance/privacy-law-compliance](https://shopify.dev/docs/apps/build/compliance/privacy-law-compliance): "If a customer hasn't placed an order in the past six months, then Shopify sends the payload 10 days after the deletion request."
- **Config:** Subscribe in shopify.app.toml with compliance_topics (not topics); these cannot be subscribed through the Admin API.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/subscribe](https://shopify.dev/docs/apps/build/webhooks/subscribe): "Cannot be subscribed to using the Admin API."

## Pitfalls the provider warns about

- **1:** Answer within 5 seconds; queue work; redirects count as errors.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/verify-deliveries](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries): "Queuing is a useful pattern for handling bursts of traffic and for ensuring you respond within five seconds."
- **2:** Do not rely on webhooks alone; build reconciliation.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks](https://shopify.dev/docs/apps/build/webhooks): "Your app shouldn't rely on receiving data from Shopify webhooks."
- **3:** Failing Admin-API subscriptions are deleted after 8 consecutive failures, silently except for warning emails.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/verify-deliveries](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries): "After 8 consecutive failures, the subscription is automatically deleted if it was configured using the Admin API."
- **4:** Body parser middleware before verification breaks HMAC.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/verify-deliveries](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries): "Place your webhook verification middleware before any body parsing middleware in your app."
- **5:** A shop-specific to app-specific migration can double-deliver unless old subscriptions are removed first.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/subscribe](https://shopify.dev/docs/apps/build/webhooks/subscribe): "remove any existing webhook subscriptions to the same topics. This avoids potential conflicts and duplicate notifications."
- **6:** Compliance webhooks cannot be created through the Admin API, only in app config or Dev Dashboard.
  Read 2026-10-20 from [shopify.dev/docs/apps/build/webhooks/subscribe](https://shopify.dev/docs/apps/build/webhooks/subscribe): "You can create mandatory compliance webhook subscriptions in Dev Dashboard or by updating your app configuration file."

## Conflicting or product-specific rules

- **What happens to a subscription after repeated failures:** Pages differ in scope, not in numbers. The verify page and the subscriptions table say deletion applies to Admin API (shop-specific) subscriptions and not to TOML app-specific ones; the troubleshoot page states removal without that qualification.
  - Read 2026-10-20 from https://shopify.dev/docs/apps/build/webhooks/subscribe: "Failing subscriptions will not be deleted by Shopify."
  - Read 2026-10-20 from https://shopify.dev/docs/apps/build/webhooks/troubleshoot: "but if failures persist, the subscription is removed."

## In WebhookVault

What WebhookVault does with Shopify requests, read from its provider catalogue on 2026-10-20. These are facts about WebhookVault, not about Shopify.

- **Signature header it reads:** `X-Shopify-Hmac-Sha256`
- **Checks the signature:** yes (HMAC-SHA256 base64 of the raw body)
- **Secret field label:** Signing secret
- **Where it finds the event name:** header `X-Shopify-Topic`
- **Where the capture URL goes in Shopify:** Settings > Notifications > Webhooks > Create webhook
