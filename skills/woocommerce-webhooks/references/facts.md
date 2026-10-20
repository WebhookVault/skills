# WooCommerce webhook facts

Generated from `data/providers/woocommerce.json` by `tools/provider-facts.mjs`; change the data and regenerate, never this file.
Every fact was read from WooCommerce's own pages on the date shown, with the sentence it came from. Quotes are verbatim except that long dashes are written as hyphens. "not stated by the provider" means the pages read did not say; it does not mean there is no rule.

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

- **Signature header:** X-WC-Webhook-Signature
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "$http_args['headers']['X-WC-Webhook-Signature'] = $this->generate_signature( $http_args['body'] );"
- **Scheme:** HMAC-SHA256 (default algorithm, filterable via woocommerce_webhook_hash_algorithm), raw binary digest, then base64 encoded
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "return base64_encode( hash_hmac( $hash_algo, $payload, wp_specialchars_decode( $this->get_secret(), ENT_QUOTES ), true ) );"
- **Signed content:** The exact request body string that is sent: trim( wp_json_encode( $payload ) ). The signature is generated from that already-encoded string (JSON by default).
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "'body' => trim( wp_json_encode( $payload ) ),"
- **Header format:** Bare base64 string, no prefix, no timestamp, one signature
  Read 2026-10-20 from [woocommerce.github.io/woocommerce-rest-api-docs/](https://woocommerce.github.io/woocommerce-rest-api-docs/): "X-WC-Webhook-Signature - a base64 encoded HMAC-SHA256 hash of the payload."
- **Where the secret comes from:** A secret set on the webhook in WooCommerce (Settings > Advanced > Webhooks > Secret field, or the REST API `secret` property). Left blank in the admin screen, the source generates a 50-character password. The woocommerce.com doc says a blank secret defaults to the current API user's consumer secret; see conflicts.
  Read 2026-10-20 from [woocommerce.com/document/webhooks/](https://woocommerce.com/document/webhooks/): "Secret - Enter a secret key used to generate a hash of the delivered webhook. The hash is included in the request headers."
- **Secret scope:** Per webhook (each webhook record has its own `secret`)
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "Get the secret used for generating the HMAC-SHA256 signature."
- **Timestamp tolerance:** not stated by the provider (the signature covers the body only; no timestamp header is sent)
  Checked 2026-10-20 at [woocommerce.github.io/woocommerce-rest-api-docs/](https://woocommerce.github.io/woocommerce-rest-api-docs/).
- **Secret rotation:** not stated by the provider (updating the secret on the webhook replaces it; no dual signing is documented)
  Checked 2026-10-20 at [woocommerce.com/document/webhooks/](https://woocommerce.com/document/webhooks/).
- **Raw body:** The signature is over the exact encoded body string; no prose from the provider about raw body handling beyond the source comment
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "Note that the signature"
- **Scheme doc comment:** The source comment describes it as a base64-encoded HMAC-SHA256 of the payload body
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "Generate a base64-encoded HMAC-SHA256 signature of the payload body"
- **Hash algorithm filter:** The algorithm defaults to sha256 but a site can change it with the woocommerce_webhook_hash_algorithm filter
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "$hash_algo = apply_filters( 'woocommerce_webhook_hash_algorithm', 'sha256', $payload, $this->get_id() );"
- **Signed content note:** Source comment: the signature is calculated after the body has been encoded
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "is calculated after the body has already been encoded (JSON by default)."
- **Secret default in admin source:** Admin screen: posted secret if given, otherwise wp_generate_password( 50, true, true )
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/admin/class-wc-admin-webhooks.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/admin/class-wc-admin-webhooks.php): ": wp_generate_password( 50, true, true );"
- **Secret default in rest source:** REST create: request secret if given, otherwise wp_generate_password( 50, true, true )
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/rest-api/Controllers/Version1/class-wc-rest-webhooks-v1-controller.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/rest-api/Controllers/Version1/class-wc-rest-webhooks-v1-controller.php): "$webhook->set_secret( ! empty( $request['secret'] ) ? $request['secret'] : wp_generate_password( 50, true, true ) );"
- **Secret html decoding:** The secret is passed through wp_specialchars_decode( ..., ENT_QUOTES ) before it is used as the HMAC key, so a secret stored with HTML entities is decoded first
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "wp_specialchars_decode( $this->get_secret(), ENT_QUOTES )"
- **Secret filter:** The secret can be overridden by the woocommerce_webhook_secret filter at read time
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "return apply_filters( 'woocommerce_webhook_secret', $this->get_prop( 'secret', $context ), $this->get_id() );"
- **Official helper (Node.js):** not stated by the provider
  Checked 2026-10-20 at [woocommerce.github.io/woocommerce-rest-api-docs/](https://woocommerce.github.io/woocommerce-rest-api-docs/).
- **Official helper (Python):** not stated by the provider
  Checked 2026-10-20 at [woocommerce.github.io/woocommerce-rest-api-docs/](https://woocommerce.github.io/woocommerce-rest-api-docs/).
- **Official helper (.NET):** not stated by the provider
  Checked 2026-10-20 at [woocommerce.github.io/woocommerce-rest-api-docs/](https://woocommerce.github.io/woocommerce-rest-api-docs/).

## Delivery

- **Method and content type:** POST, Content-Type application/json, redirects not followed (redirection 0), request timeout 60 seconds
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "'Content-Type' => 'application/json',"
- **Event name:** Headers X-WC-Webhook-Topic (resource.event, e.g. order.updated), X-WC-Webhook-Resource and X-WC-Webhook-Event. The JSON body does not carry the topic.
  Read 2026-10-20 from [woocommerce.github.io/woocommerce-rest-api-docs/](https://woocommerce.github.io/woocommerce-rest-api-docs/): "X-WC-Webhook-Topic - e.g. order.updated"
- **Delivery or event id:** X-WC-Webhook-Delivery-ID header. The source builds it as wp_hash( webhook_id . strtotime( 'now' ) ), a hash of the webhook ID and the current time in whole seconds.
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "return wp_hash( $this->get_id() . strtotime( 'now' ) );"
- **Handshake:** A ping is sent to the delivery URL when a webhook is first created / first saved as Active: a POST whose body is the string `webhook_id=<id>` (form-style, not JSON). The ping args set only user-agent and body in the source (no Content-Type, no X-WC-Webhook-* headers, no signature). The ping must be answered with exactly 200.
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "'body' => 'webhook_id=' . $this->get_id(),"
- **Events per request:** One event per request (one payload built from one hook argument per delivery)
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "$payload = $this->build_payload( $arg );"
- **Method:** POST
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "'method' => 'POST',"
- **User agent:** WooCommerce/<WC_VERSION> Hookshot (WordPress/<wp_version>)
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "'user-agent' => sprintf( 'WooCommerce/%s Hookshot (WordPress/%s)', Constants::get_constant( 'WC_VERSION' ), $GLOBALS['wp_version'] ),"
- **Headers x wc webhook source:** X-WC-Webhook-Source: the site's home URL with trailing slash (home_url( '/' ))
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "$http_args['headers']['X-WC-Webhook-Source'] = home_url( '/' ); // Since 2.6.0."
- **Headers x wc webhook topic:** X-WC-Webhook-Topic: the topic, e.g. order.updated
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "$http_args['headers']['X-WC-Webhook-Topic'] = $this->get_topic();"
- **Headers x wc webhook resource:** X-WC-Webhook-Resource: the resource, e.g. order
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "$http_args['headers']['X-WC-Webhook-Resource'] = $this->get_resource();"
- **Headers x wc webhook event:** X-WC-Webhook-Event: the event, e.g. updated
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "$http_args['headers']['X-WC-Webhook-Event'] = $this->get_event();"
- **Headers x wc webhook id:** X-WC-Webhook-ID: the numeric ID of the webhook (not the delivery)
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "$http_args['headers']['X-WC-Webhook-ID'] = $this->get_id();"
- **Headers x wc webhook delivery id:** X-WC-Webhook-Delivery-ID: a hash generated per delivery
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "$http_args['headers']['X-WC-Webhook-Delivery-ID'] = $delivery_id;"
- **Headers x wc webhook signature:** X-WC-Webhook-Signature: see the signature section
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "$http_args['headers']['X-WC-Webhook-Signature'] = $this->generate_signature( $http_args['body'] );"
- **Id comment:** Source comment on how the ID is generated
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "we generate a unique hash instead based on current time and webhook ID."
- **Payload:** JSON; for the API resources (coupons, customers, orders, products) the body is the same as the REST API response for that resource. Custom `action.*` topics pass the first hook argument.
  Read 2026-10-20 from [woocommerce.github.io/woocommerce-rest-api-docs/](https://woocommerce.github.io/woocommerce-rest-api-docs/): "the response is exactly the same as if requested via the REST API."
- **Ping when:** Sent when a webhook is first created and when it is first activated
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "Send a test ping to the delivery URL, sent when the webhook is first created."
- **Ping when doc:** The first time a webhook is saved with Active status
  Read 2026-10-20 from [woocommerce.com/document/webhooks/](https://woocommerce.com/document/webhooks/): "The first time you save a webhook with the Active status, WooCommerce sends a ping to the Delivery URL."
- **Ping success:** Only HTTP 200 counts for the ping; any other code or an unreachable URL returns an error to the admin screen
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "if ( 200 !== $response_code ) {"
- **Ping in rest:** Creating a webhook through the REST API also sends a ping
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/rest-api/Controllers/Version1/class-wc-rest-webhooks-v1-controller.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/rest-api/Controllers/Version1/class-wc-rest-webhooks-v1-controller.php): "// Send ping."
- **Async delivery:** Delivery is queued at the end of the request (shutdown hook) and by default run in the background through WooCommerce's queue as the woocommerce_deliver_webhook_async action in group woocommerce-webhooks; woocommerce_webhook_deliver_async can force immediate delivery
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/wc-webhook-functions.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/wc-webhook-functions.php): "Webhooks are processed in the background by default"
- **Queue backend:** WC()->queue()->add is implemented with Action Scheduler (as_schedule_single_action)
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/queue/class-wc-action-queue.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/queue/class-wc-action-queue.php): "return as_schedule_single_action( $timestamp, $hook, $args, $group );"
- **Coalescing window:** The same webhook with the same hook arguments is scheduled at most once per 10 minutes (an already-pending action is not duplicated)
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/wc-webhook-functions.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/wc-webhook-functions.php): "only schedule one webhook every 10 minutes to maintain backward compatibility with WP Cron behaviour seen in WC < 3.5.0."
- **Rest doc async statement:** The REST docs say delivery is processed in the background using wp-cron (see conflicts)
  Read 2026-10-20 from [woocommerce.github.io/woocommerce-rest-api-docs/](https://woocommerce.github.io/woocommerce-rest-api-docs/): "processed in the background by default using wp-cron."

## Responding and retries

- **Expected response:** Any 2xx, plus 301 and 302 (the doc wording). The source condition counts any code from 200 up to and including 302 as success; redirects are not followed.
  Read 2026-10-20 from [woocommerce.com/document/webhooks/](https://woocommerce.com/document/webhooks/): "A failure is any response that is not a 2xx, 301, or 302 HTTP status code."
- **Response deadline:** 60 seconds (HTTP timeout set to MINUTE_IN_SECONDS); not documented in prose
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "'timeout' => MINUTE_IN_SECONDS,"
- **Retries:** not stated by the provider. The source performs one wp_safe_remote_request per scheduled delivery and I found no retry logic in class-wc-webhook.php or wc-webhook-functions.php; a failed delivery only increments the consecutive-failure counter.
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "$response = wp_safe_remote_request( $this->get_delivery_url(), $http_args );"
- **Disabling after failures:** Webhook status becomes `disabled` after more than five consecutive failed deliveries (doc wording); threshold filter is woocommerce_max_webhook_delivery_failures (default 5); action hook woocommerce_webhook_disabled_due_delivery_failures fires. A re-enable requires editing the webhook (status back to Active).
  Read 2026-10-20 from [woocommerce.com/document/webhooks/](https://woocommerce.com/document/webhooks/): "WooCommerce automatically disables a webhook after more than five consecutive delivery failures."
- **Ordering:** not stated by the provider (deliveries are independent background actions)
  Checked 2026-10-20 at [woocommerce.com/document/webhooks/](https://woocommerce.com/document/webhooks/).
- **Duplicates:** not stated by the provider. Source suppresses re-processing of the same hook argument within one request and coalesces identical pending deliveries (see coalescing_window).
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/wc-webhook-functions.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/wc-webhook-functions.php): "Make webhooks unique"
- **Success status source:** Code: response >= 200 and < 303 resets the failure counter
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "if ( intval( $response_code ) >= 200 && intval( $response_code ) < 303 ) {"
- **Redirects:** Redirects are not followed (a 301/302 is read as the response and counted as success)
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "'redirection' => 0,"
- **Disabling filter:** woocommerce_max_webhook_delivery_failures, default 5
  Read 2026-10-20 from [woocommerce.com/document/webhooks/](https://woocommerce.com/document/webhooks/): "you can use the woocommerce_max_webhook_delivery_failures filter."
- **Disabling source:** Source condition is `$failures > <filter, default 5>` evaluated before the counter is incremented; when true the status is set to disabled. (Reading of the code, not provider prose: the counter reaches 6 on the sixth consecutive failure and the webhook is disabled when the seventh consecutive failed delivery is processed.)
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "if ( $failures > apply_filters( 'woocommerce_max_webhook_delivery_failures', 5 ) ) {"
- **Disabling failure definition source comment:** Source comment defines the rule as more than 5 consecutive failures
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "if more than 5 consecutive failures occur."
- **Status values:** active (delivers), paused (paused by admin), disabled (paused automatically due to consecutive failures)
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "'disabled' - does not delivery payload, paused automatically due to consecutive failures."

## Events

Full list: https://woocommerce.github.io/woocommerce-rest-api-docs/#webhooks

- **Topics core doc:** Core topics: coupon.created/updated/deleted, customer.created/updated/deleted, order.created/updated/deleted, product.created/updated/deleted (docs); plus action.<hook> custom topics
  Read 2026-10-20 from [woocommerce.github.io/woocommerce-rest-api-docs/](https://woocommerce.github.io/woocommerce-rest-api-docs/): "Orders: order.created, order.updated and order.deleted."

- **Topics source events:** Source accepts resources coupon, customer, order, product with events created, updated, deleted, restored, published, but only pairs that have a registered hook are valid (e.g. order.published and customer.restored are rejected)
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/wc-webhook-functions.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/wc-webhook-functions.php): "$default_events = array( 'created', 'updated', 'deleted', 'restored', 'published' );"

- **Topics invalid pairs:** Default pairs with no registered hook are rejected
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/wc-webhook-functions.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/wc-webhook-functions.php): "(e.g. `order.published`, `customer.restored`) are rejected"

- **`order.created`:** A new order was created (hook woocommerce_new_order)
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "'woocommerce_new_order',"
- **`order.updated`:** Order updated; also fires on order refunds and refund deletion
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "'woocommerce_order_refunded',"
- **`order.deleted`:** Order trashed (hooks wp_trash_post, woocommerce_trash_order)
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "'woocommerce_trash_order',"
- **`order.restored`:** Order restored from the trash
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "'woocommerce_untrash_order',"
- **`product.created`:** Product or variation created
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "'woocommerce_new_product_variation',"
- **`product.updated`:** Product or variation updated
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "'woocommerce_update_product_variation',"
- **`customer.created`:** Customer account created
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "'woocommerce_new_customer',"
- **`coupon.created`:** Coupon created
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "'woocommerce_new_coupon',"
- **`action.<hook_name> (e.g. action.woocommerce_add_to_cart)`:** Custom topic that fires when a WooCommerce action runs; names must start with action.woocommerce_ or action.wc_
  Read 2026-10-20 from [woocommerce.com/document/webhooks/](https://woocommerce.com/document/webhooks/): "you can create a webhook that fires every time a product is added to the shopping cart by using the action woocommerce_add_to_cart"

## Setup and testing

- **Where the URL goes:** WooCommerce > Settings > Advanced > Webhooks > Add webhook (Delivery URL field), or POST /wp-json/wc/v3/webhooks
  Read 2026-10-20 from [woocommerce.com/document/webhooks/](https://woocommerce.com/document/webhooks/): "Go to WooCommerce > Settings > Advanced > Webhooks."
- **Test tools:** The ping on first activation; delivery logs under WooCommerce > Status > Logs (source webhooks-delivery) recording request duration, URL, headers, body and the response. No send-test-event or redelivery button is documented.
  Read 2026-10-20 from [woocommerce.com/document/webhooks/](https://woocommerce.com/document/webhooks/): "select webhooks-delivery from the All sources dropdown to filter the list."
- **Source IP addresses:** not stated by the provider (webhooks are sent from the merchant's own site; X-WC-Webhook-Source names that site)
  Checked 2026-10-20 at [woocommerce.github.io/woocommerce-rest-api-docs/](https://woocommerce.github.io/woocommerce-rest-api-docs/).
- **Fields:** Name, Status (Active / Paused / Disabled), Topic, Custom Topic, Action Event, Delivery URL, Secret
  Read 2026-10-20 from [woocommerce.com/document/webhooks/](https://woocommerce.com/document/webhooks/): "Delivery URL - Enter the URL where the webhook payload is delivered."
- **Url schemes:** Delivery URL must be HTTP or HTTPS
  Read 2026-10-20 from [woocommerce.github.io/woocommerce-rest-api-docs/](https://woocommerce.github.io/woocommerce-rest-api-docs/): "URL where the payload is delivered, must be HTTP or HTTPS."
- **Logging:** Request and response are logged; the body is only logged in WP_DEBUG mode
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "Webhook body is not logged unless WP_DEBUG mode is turned on."

## Pitfalls the provider warns about

- **1:** The ping body is the plain string webhook_id=<id>, not JSON, and is not signed; a receiver that JSON-parses or verifies signatures on every POST will reject it, and the ping must return exactly 200 or the admin save reports an error
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php): "return new WP_Error( 'error', sprintf( __( 'Error: Delivery URL returned response code: %s', 'woocommerce' ), absint( $response_code ) ) );"
- **2:** Failures are consecutive failed deliveries; any success resets the counter, and a webhook disabled by failures must be re-enabled by editing it
  Read 2026-10-20 from [woocommerce.github.io/woocommerce-rest-api-docs/](https://woocommerce.github.io/woocommerce-rest-api-docs/): "the webhook is disabled and must be edited via the REST API to re-enable."
- **3:** 4xx and 5xx responses count as failures
  Read 2026-10-20 from [woocommerce.com/document/webhooks/](https://woocommerce.com/document/webhooks/): "For example, 4xx or 5xx responses count as failures."
- **4:** Payload for API resources mirrors the REST API response, so shapes follow the REST API version configured on the webhook
  Read 2026-10-20 from [woocommerce.github.io/woocommerce-rest-api-docs/](https://woocommerce.github.io/woocommerce-rest-api-docs/): "the response is exactly the same as if requested via the REST API."
- **5:** Identical pending deliveries are coalesced within 10 minutes, so rapid repeated updates of the same record may produce fewer webhooks than changes
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/wc-webhook-functions.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/wc-webhook-functions.php): "Make webhooks unique - only schedule one webhook every 10 minutes"
- **6:** Webhooks are delivered in the background so delivery lag depends on the site's queue runner (Action Scheduler), not on the triggering request
  Read 2026-10-20 from [github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/wc-webhook-functions.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/wc-webhook-functions.php): "Webhooks are processed in the background by default"

## Conflicting or product-specific rules

- **Default secret when left blank (woocommerce.com doc vs source):** Default secret when left blank (woocommerce.com doc vs source)
  - Read 2026-10-20 from https://woocommerce.com/document/webhooks/: "If you leave this blank, it defaults to the current API user’s consumer secret."
  - Read 2026-10-20 from https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/admin/class-wc-admin-webhooks.php: ": wp_generate_password( 50, true, true );"
- **Default secret in the REST API (REST docs vs source):** Default secret in the REST API (REST docs vs source)
  - Read 2026-10-20 from https://woocommerce.github.io/woocommerce-rest-api-docs/: "This will default is a MD5 hash from the current user's ID|username if not provided."
  - Read 2026-10-20 from https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/rest-api/Controllers/Version1/class-wc-rest-webhooks-v1-controller.php: "$webhook->set_secret( ! empty( $request['secret'] ) ? $request['secret'] : wp_generate_password( 50, true, true ) );"
- **Background delivery mechanism (REST docs say wp-cron, source uses Action Scheduler):** Background delivery mechanism (REST docs say wp-cron, source uses Action Scheduler)
  - Read 2026-10-20 from https://woocommerce.github.io/woocommerce-rest-api-docs/: "processed in the background by default using wp-cron."
  - Read 2026-10-20 from https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/queue/class-wc-action-queue.php: "return as_schedule_single_action( $timestamp, $hook, $args, $group );"
- **Failure threshold wording (REST docs: after 5; woocommerce.com doc and source: more than 5):** Failure threshold wording (REST docs: after 5; woocommerce.com doc and source: more than 5)
  - Read 2026-10-20 from https://woocommerce.github.io/woocommerce-rest-api-docs/: "After 5 consecutive failed deliveries"
  - Read 2026-10-20 from https://woocommerce.com/document/webhooks/: "WooCommerce automatically disables a webhook after more than five consecutive delivery failures."
- **Delivery ID (REST docs say a comment ID; source generates a hash):** Delivery ID (REST docs say a comment ID; source generates a hash)
  - Read 2026-10-20 from https://woocommerce.github.io/woocommerce-rest-api-docs/: "X-WC-Webhook-Delivery-ID - delivery log ID (a comment)."
  - Read 2026-10-20 from https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/class-wc-webhook.php: "Since we no longer use comments to store delivery logs"
- **Success status codes (REST docs: 2xx; woocommerce.com doc and source: also 301/302):** Success status codes (REST docs: 2xx; woocommerce.com doc and source: also 301/302)
  - Read 2026-10-20 from https://woocommerce.github.io/woocommerce-rest-api-docs/: "(as defined by a non HTTP 2xx response code)"
  - Read 2026-10-20 from https://woocommerce.com/document/webhooks/: "A failure is any response that is not a 2xx, 301, or 302 HTTP status code."

## In WebhookVault

What WebhookVault does with WooCommerce requests, read from its provider catalogue on 2026-10-20. These are facts about WebhookVault, not about WooCommerce.

- **Signature header it reads:** `X-WC-Webhook-Signature`
- **Checks the signature:** yes (HMAC-SHA256 base64 of the raw body)
- **Secret field label:** Signing secret
- **Where it finds the event name:** header `X-WC-Webhook-Topic`
- **Where the capture URL goes in WooCommerce:** WooCommerce > Settings > Advanced > Webhooks > Add webhook
