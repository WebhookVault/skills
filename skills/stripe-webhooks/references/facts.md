# Stripe webhook facts

Generated from `data/providers/stripe.json` by `tools/provider-facts.mjs`; change the data and regenerate, never this file.
Every fact was read from Stripe's own pages on the date shown, with the sentence it came from. Quotes are verbatim except that long dashes are written as hyphens. "not stated by the provider" means the pages read did not say; it does not mean there is no rule.

## Contents

- [Signature](#signature)
- [Delivery](#delivery)
- [Responding and retries](#responding-and-retries)
- [Events](#events)
- [Setup and testing](#setup-and-testing)
- [Extras](#extras)
- [Pitfalls the provider warns about](#pitfalls-the-provider-warns-about)
- [In WebhookVault](#in-webhookvault)

## Signature

- **Signature header:** Stripe-Signature
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "Stripe signs every webhook event by including a signature in the Stripe-Signature header."
- **Scheme:** HMAC-SHA256 (the docs do not say the encoding in words; the header example shows lowercase hex digests). Only scheme v1 is valid for live events; ignore all other schemes.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "Stripe generates signatures using a hash-based message authentication code (HMAC) with SHA-256. To prevent downgrade attacks, ignore all schemes that aren't v1."
- **Signed content:** The timestamp (as a string), then the character '.', then the actual JSON payload (the raw request body). HMAC key is the endpoint's signing secret.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "Compute an HMAC with the SHA256 hash function. Use the endpoint's signing secret as the key, and use the signed_payload string as the message."
- **Header format:** Single-line header of comma-separated key=value elements: t=<unix timestamp>, one or more v1=<signature>, and (test events) a fake v0=<signature>. Split on ',' then on '='; use t and every v1, discard the rest. Multiple v1 values appear while a rolled secret is still active.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "The timestamp has a t= prefix"
- **Where the secret comes from:** The endpoint's signing secret, starting whsec_: in the Dashboard (Workbench, Webhooks tab, Reveal secret) or returned as signing_secret when the endpoint is created through the API. The Stripe CLI uses its own signing secret, different from a Dashboard endpoint's.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "a signing secret beginning with whsec_ appears. Click Reveal secret and copy the value"
- **Secret scope:** Per endpoint, and different again for test and live on the same URL
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "Stripe generates a unique secret key for each endpoint. If you use the same endpoint for both test and live API keys, the secret is different for each one."
- **Timestamp tolerance:** Official libraries default to 5 minutes between the header timestamp and current time; configurable by an extra parameter. A tolerance of 0 disables the recency check entirely. A new signature and timestamp are generated for every delivery attempt, including retries.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "Our libraries have a default tolerance of 5 minutes between the timestamp and the current time. You can change this tolerance by providing an additional parameter when verifying signatures."
- **Secret rotation:** Roll secret in Workbench; the old secret can expire immediately or stay active up to 24 hours. While both are active Stripe sends one v1 signature per active secret, so the header carries multiple v1 values.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "You can choose to immediately expire the current secret or delay its expiration for up to 24 hours to allow yourself time to update the verification code on your server."
- **Raw body:** Stripe requires the raw body; any framework manipulation (reordering keys, stripping whitespace, converting to JSON, changing encoding) breaks verification. Body must be the exact UTF-8 string Stripe sent. With Express, register the webhook route with express.raw before express.json.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "Stripe requires the raw body of the request to perform signature verification. If you're using a framework, make sure it doesn't manipulate the raw body."
- **Signed content parts:** signed_payload = timestamp-as-string + '.' + request body
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "The actual JSON payload (that is, the request body)"
- **Secret scope cli:** The secret for a CLI-forwarded endpoint is different from the secret for a Dashboard-managed endpoint.
  Read 2026-10-20 from [docs.stripe.com/events/manage-webhook-endpoints](https://docs.stripe.com/events/manage-webhook-endpoints): "The secret for a CLI-forwarded endpoint is different from the secret for a Dashboard-managed endpoint"
- **Tolerance zero warning:** A tolerance of 0 disables the recency check.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "Using a tolerance value of 0 disables the recency check entirely."
- **Retry resigns:** Each retry gets a fresh timestamp and signature.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "If Stripe retries an event (for example, your endpoint previously replied with a non-2xx status code), then we generate a new signature and timestamp for the new delivery attempt."
- **Rotation multiple signatures:** Multiple v1 signatures in one header during the overlap.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "During this time, multiple secrets are active for the endpoint. Stripe generates one signature per secret until expiration."
- **Raw body utf8:** Exact UTF-8 string, unmodified.
  Read 2026-10-20 from [docs.stripe.com/events/manage-webhook-endpoints](https://docs.stripe.com/events/manage-webhook-endpoints): "The request body must be the exact UTF-8 string Stripe sent, without any modifications."
- **Comparison note:** Compare each v1 signature with the expected one using a constant-time string comparison.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "To protect against timing attacks, use a constant-time-string comparison to compare the expected signature to each of the received signatures."
- **Published test vector note:** The docs show only an illustrative header (t=1492774577, v1=5257a869..., v0=6ffbb59b...) with no secret or body, so there is no complete worked example to copy.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "t=1492774577, v1=5257a869e7ecebeda32affa62cdca3fa51cad7e77a0e56ff536d0ce8e108d8bd, v0=6ffbb59b2300aae63f272406069a9788598b792a944a07aba816edb039989a39"
- **Official helper (Node.js):** stripe.webhooks.constructEvent(request.body, signature, endpointSecret) for snapshot events; client.parseEventNotification(request.body, sig, endpointSecret) for thin events
  Read 2026-10-20 from [docs.stripe.com/events/set-up-events](https://docs.stripe.com/events/set-up-events): "event = stripe.webhooks.constructEvent(request.body, sig, endpointSecret);"
- **Official helper (Python):** client.construct_event(payload, sig_header, endpoint_secret) on a stripe.StripeClient (webhooks quickstart); client.parse_event_notification(webhook_body, sig_header, webhook_secret) for thin events
  Read 2026-10-20 from [docs.stripe.com/webhooks/quickstart](https://docs.stripe.com/webhooks/quickstart): "event = client.construct_event( payload, sig_header, endpoint_secret )"
- **Official helper (.NET):** EventUtility.ConstructEvent(json, signatureHeader, endpointSecret) (Stripe.net)
  Read 2026-10-20 from [docs.stripe.com/webhooks/quickstart](https://docs.stripe.com/webhooks/quickstart): "stripeEvent = EventUtility.ConstructEvent(json, signatureHeader, endpointSecret);"

## Delivery

- **Method and content type:** HTTPS POST with a JSON payload. Content-Type header value is not stated by the provider.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "Handles POST requests with a JSON payload that includes event information."
- **Event name:** Top-level 'type' field of the JSON body; event id in top-level 'id'; related resource under data (snapshot) or related_object (thin).
  Read 2026-10-20 from [docs.stripe.com/webhooks/quickstart](https://docs.stripe.com/webhooks/quickstart): "Each event is structured as an Event object with a type, id, and related Stripe resource nested under data."
- **Delivery or event id:** Event id (evt_...) in the body. Dedupe on it. In some cases two separate Event objects are generated for one occurrence; to catch those use the id of data.object together with event.type. Do not use 'created' to order or dedupe.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "Webhook endpoints might occasionally receive the same event more than once. You can guard against duplicated event receipts by logging the event IDs you've processed"
- **Handshake:** not stated by the provider (no challenge or ping on setup)
  Checked 2026-10-20 at [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks).
- **Events per request:** not stated by the provider as a batching rule; the docs describe each delivery as one Event object
  Read 2026-10-20 from [docs.stripe.com/webhooks/quickstart](https://docs.stripe.com/webhooks/quickstart): "Each event is structured as an Event object"
- **Id two objects:** Two separate Event objects can describe one occurrence.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "In some cases, two separate Event objects are generated and sent. To identify these duplicates, use the ID of the object in data.object along with the event.type."
- **Retried events same id:** not stated by the provider whether a retry carries the same event id; the docs say to track event IDs to identify duplicate deliveries
  Read 2026-10-20 from [docs.stripe.com/events/how-events-work](https://docs.stripe.com/events/how-events-work): "Track event IDs to identify duplicate deliveries instead."

## Responding and retries

- **Expected response:** Any 2xx. Redirects (3xx) are treated as failures. 4xx, 5xx, timeouts and TLS errors are failures.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "We consider redirect responses to webhook requests as failures."
- **Response deadline:** not stated by the provider (no number of seconds). The docs only say to return quickly and list 'Timed out' as a failure status.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "The destination server took too long to respond to the webhook request."
- **Retries:** Live mode: up to three days with exponential back off. Sandbox: three retries over a few hours (the page says sandbox; it does not use the words test mode). Next retry time is shown in the Event deliveries tab.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "Stripe attempts to deliver events to your destination for up to three days with an exponential back off in live mode."
- **Disabling after failures:** not stated by the provider: no page read says Stripe disables an endpoint after repeated failures. The pages only describe manual disable/re-enable, and the webhook endpoint object has a status of enabled or disabled.
  Read 2026-10-20 from [docs.stripe.com/api/webhook_endpoints/object](https://docs.stripe.com/api/webhook_endpoints/object): "The status of the webhook. It can be enabled or disabled."
- **Ordering:** Not guaranteed. Do not rely on created (seconds resolution, can tie); fetch missing objects from the API.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "Stripe doesn't guarantee the delivery of events in the order that they're generated."
- **Duplicates:** Can occur; log processed event ids and skip repeats.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "Webhook endpoints might occasionally receive the same event more than once."
- **Success status 2xx:** Return 2xx before running any complex logic.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "Quickly returns a successful status code (2xx) before any complex logic that might cause a timeout."
- **Retries sandbox:** Sandbox deliveries: three retries over a few hours.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "We retry event deliveries created in a sandbox three times over the course of a few hours."
- **Retries disabled destination:** Disabling or deleting a destination stops pending retries, unless it is re-enabled before the retry is attempted.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "If your destination has been disabled or deleted when we attempt a retry, we prevent future retries of that event."
- **Disabling manual:** After you disable an event destination Stripe stops sending events to it; after re-enable Stripe resumes.
  Read 2026-10-20 from [docs.stripe.com/events/how-events-work](https://docs.stripe.com/events/how-events-work): "After you disable an event destination, Stripe stops sending any events to that destination. After you re-enable a destination, Stripe resumes sending events to it."
- **Manual resend:** Dashboard Resend works up to 15 days after event creation; CLI 'stripe events resend <event_id> --webhook-endpoint=<endpoint_id>' works up to 30 days. A manual resend does not cancel automatic retries, even if it returns 2xx; answer 2xx to an already-processed event to stop retries.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "Manually resending an event that failed to reach a webhook endpoint doesn't cancel Stripe's automatic retry behavior, even if it results in a 2xx status code."
- **Tls:** TLS 1.2 or 1.3 only; HTTPS URL required in live mode.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "If you use an HTTPS URL for your webhook endpoint (required in live mode)"

## Events

Full list: https://docs.stripe.com/api/events/types

Note: https://docs.stripe.com/api/v2/core/events/event-types

- **`checkout.session.completed`:** A Checkout Session finished successfully; typical trigger for fulfilment.
  Read 2026-10-20 from [docs.stripe.com/api/events/types](https://docs.stripe.com/api/events/types): "Occurs when a Checkout Session has been successfully completed."
- **`payment_intent.succeeded`:** A PaymentIntent completed payment.
  Read 2026-10-20 from [docs.stripe.com/api/events/types](https://docs.stripe.com/api/events/types): "Occurs when a PaymentIntent has successfully completed payment."
- **`payment_intent.payment_failed`:** A payment attempt on a PaymentIntent failed.
  Read 2026-10-20 from [docs.stripe.com/api/events/types](https://docs.stripe.com/api/events/types): "Occurs when a PaymentIntent has failed the attempt to create a payment method or a payment."
- **`invoice.paid`:** An invoice was paid, or marked paid out of band.
  Read 2026-10-20 from [docs.stripe.com/api/events/types](https://docs.stripe.com/api/events/types): "Occurs whenever an invoice payment attempt succeeds or an invoice is marked as paid out-of-band."
- **`invoice.payment_failed`:** An invoice payment attempt failed (decline or no stored payment method).
  Read 2026-10-20 from [docs.stripe.com/api/events/types](https://docs.stripe.com/api/events/types): "Occurs whenever an invoice payment attempt fails"
- **`customer.subscription.created`:** A customer was signed up for a new plan.
  Read 2026-10-20 from [docs.stripe.com/api/events/types](https://docs.stripe.com/api/events/types): "Occurs whenever a customer is signed up for a new plan."
- **`customer.subscription.updated`:** A subscription changed (plan switch, status change such as trial to active).
  Read 2026-10-20 from [docs.stripe.com/api/events/types](https://docs.stripe.com/api/events/types): "Occurs whenever a subscription changes"
- **`customer.subscription.deleted`:** A subscription ended.
  Read 2026-10-20 from [docs.stripe.com/api/events/types](https://docs.stripe.com/api/events/types): "subscription ends."
- **`charge.refunded`:** A charge was refunded, including partially.
  Read 2026-10-20 from [docs.stripe.com/api/events/types](https://docs.stripe.com/api/events/types): "Occurs whenever a charge is refunded, including partial refunds."
- **`charge.dispute.created`:** A customer disputed a charge with their bank.
  Read 2026-10-20 from [docs.stripe.com/api/events/types](https://docs.stripe.com/api/events/types): "Occurs whenever a customer disputes a charge with their bank."

## Setup and testing

- **Where the URL goes:** Workbench Webhooks tab: Create an event destination, choose Your account or Connected accounts, choose payload format Thin or Snapshot, select event types, destination type Webhook endpoint, then the URL. Or API: POST /v2/core/event_destinations. Maximum 16 event destinations.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "You can register up to 16 event destinations with Stripe. Registered webhook endpoints must be publicly accessible HTTPS URLs."
- **Test tools:** The Stripe CLI's 'stripe trigger <event>' creates test objects and fires the events they cause; events can be resent from the Dashboard (up to 15 days) or with 'stripe events resend' (up to 30 days).
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "Because of this, triggering events causes side effects: all necessary API objects will be created in the process."
- **Source IP addresses:** Published list on the domains and IP addresses page, also downloadable as ips_webhooks.txt and ips_webhooks.json. Stripe gives seven days' notice of changes through the API announce mailing list. Docs recommend IP allowlisting together with (not instead of) signature verification.
  Read 2026-10-20 from [docs.stripe.com/ips](https://docs.stripe.com/ips): "https://stripe.com/files/ips/ips_webhooks.txt"
- **Cli trigger effects:** stripe trigger makes real API calls in the test environment, so it has side effects and may emit several events.
  Read 2026-10-20 from [docs.stripe.com/cli/trigger](https://docs.stripe.com/cli/trigger): "Because of this, triggering events causes side effects: all necessary API objects will be created in the process."
- **Cli trigger extra events:** One trigger can fire related events too.
  Read 2026-10-20 from [docs.stripe.com/cli/trigger](https://docs.stripe.com/cli/trigger): "triggering payment_intent.succeeded also triggers payment_intent.created"

## Extras

- **Thin vs snapshot:** Two payload formats chosen per destination. Thin: lightweight notification (type, id, created, related_object id/type/url), unversioned, typed in SDKs, fetch the resource or full event afterwards; recommended for new integrations; thin events need their own separate endpoint. Snapshot: full Event object with data.object and previous_attributes, versioned by API version.
  Read 2026-10-20 from [docs.stripe.com/events/how-events-work](https://docs.stripe.com/events/how-events-work): "For new integrations, use thin events. Thin events are unversioned, fully typed in the Stripe SDKs, and let your integration fetch the latest resource state."
- **Thin needs separate endpoint:** Register a separate endpoint for thin events.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "If you are using thin events, you will need to register a separate webhook endpoint."
- **Snapshot staleness:** Snapshot data.object can be stale; refetch before acting.
  Read 2026-10-20 from [docs.stripe.com/events/how-events-work](https://docs.stripe.com/events/how-events-work): "Because this snapshot can be stale by the time your application processes it, fetch the latest version of the resource from the API before acting on the data."
- **Connect:** Connect platforms pick a scope per endpoint: Your account, or Connected accounts. Events for connected accounts carry a top-level 'account' property. Production Connect endpoints receive both live and test webhooks (check livemode). Sandbox accounts need separate endpoints.
  Read 2026-10-20 from [docs.stripe.com/connect/webhooks](https://docs.stripe.com/connect/webhooks): "Each event for a connected account contains a top-level account property that identifies the connected account."
- **Connect livemode:** Production Connect URLs receive live and test events.
  Read 2026-10-20 from [docs.stripe.com/connect/webhooks](https://docs.stripe.com/connect/webhooks): "your development webhook URLs receive only test webhooks, but your production webhook URLs receive both live and test webhooks."
- **Connect api flag:** Webhook endpoint API 'connect' parameter: false for your account, true for connected accounts.
  Read 2026-10-20 from [docs.stripe.com/connect/webhooks](https://docs.stripe.com/connect/webhooks): "assign the scope by setting the connect parameter to false (for Your account) or true (for Connected accounts)."
- **Api version of events:** The API version in account settings when the event occurs (or the destination version for snapshot destinations) determines event structure; existing events do not change.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "The API version in your account settings when the event occurs dictates the API version, and therefore the structure of an Event sent to your destination."

## Pitfalls the provider warns about

- **1:** Do not manipulate the raw body.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "Any manipulation to the raw body of the request causes the verification to fail."
- **2:** With Express, the JSON body parser must come after the webhook route.
  Read 2026-10-20 from [docs.stripe.com/events/manage-webhook-endpoints](https://docs.stripe.com/events/manage-webhook-endpoints): "Express applies middleware in order; if express.json() runs first, it parses the body before signature verification."
- **3:** Redirects count as failures; register the final URL.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "We consider redirect responses to webhook requests as failures."
- **4:** Webhook route must be exempt from CSRF protection in frameworks such as Rails or Django.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "you might need to exempt the webhooks route from CSRF protection."
- **5:** Ignore every signature scheme other than v1 (test events also carry a fake v0).
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "To aid with testing, Stripe sends an additional signature with a fake v0 scheme, for test events."
- **6:** Using the wrong secret is the most common signature failure; the CLI secret differs from the Dashboard secret, and test and live secrets differ.
  Read 2026-10-20 from [docs.stripe.com/events/manage-webhook-endpoints](https://docs.stripe.com/events/manage-webhook-endpoints): "The most common cause is using the wrong endpoint secret."
- **7:** Process asynchronously: spikes (for example month-start renewals) can overwhelm synchronous handlers.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "Configure your handler to process incoming events with an asynchronous queue."
- **8:** Subscribe only to the event types you need.
  Read 2026-10-20 from [docs.stripe.com/webhooks](https://docs.stripe.com/webhooks): "Configure your webhook endpoints to receive only the types of events required by your integration."
- **9:** Selection-required event types are only generated when a webhook explicitly listens for them; an all-events endpoint does not trigger them.
  Read 2026-10-20 from [docs.stripe.com/api/events/types](https://docs.stripe.com/api/events/types): "A webhook set to listen to all events doesn't satisfy this requirement"
- **10:** Stripe may fail to generate an event (rare); the health event v2.core.health.event_generation_failure.resolved is sent, and you should poll the resource.
  Read 2026-10-20 from [docs.stripe.com/events/manage-webhook-endpoints](https://docs.stripe.com/events/manage-webhook-endpoints): "In rare cases, Stripe can fail to generate an Event object."

## In WebhookVault

What WebhookVault does with Stripe requests, read from its provider catalogue on 2026-10-20. These are facts about WebhookVault, not about Stripe.

- **Signature header it reads:** `Stripe-Signature`
- **Checks the signature:** yes (HMAC-SHA256 hex over "t.body" from the t and v1 values, 5 minute tolerance)
- **Secret field label:** Signing secret
- **Where it finds the event name:** body `type`
- **Where the capture URL goes in Stripe:** Developers > Webhooks > Add endpoint
