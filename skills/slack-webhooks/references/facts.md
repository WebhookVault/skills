# Slack webhook facts

Generated from `data/providers/slack.json` by `tools/provider-facts.mjs`; change the data and regenerate, never this file.
Every fact was read from Slack's own pages on the date shown, with the sentence it came from. Quotes are verbatim except that long dashes are written as hyphens. "not stated by the provider" means the pages read did not say; it does not mean there is no rule.

## Contents

- [Signature](#signature)
- [Delivery](#delivery)
- [Responding and retries](#responding-and-retries)
- [Events](#events)
- [Setup and testing](#setup-and-testing)
- [Pitfalls the provider warns about](#pitfalls-the-provider-warns-about)
- [In WebhookVault](#in-webhookvault)

## Signature

- **Signature header:** X-Slack-Signature (signature) and X-Slack-Request-Timestamp (timestamp)
  Read 2026-10-20 from [docs.slack.dev/authentication/verifying-requests-from-slack/](https://docs.slack.dev/authentication/verifying-requests-from-slack/): "On each HTTP request that Slack sends, Slack adds an X-Slack-Signature HTTP header (or x-slack-signature"
- **Scheme:** HMAC-SHA256 keyed with the app Signing Secret (used as a plain UTF-8 string), hex digest, prefixed with the literal v0=
  Read 2026-10-20 from [docs.slack.dev/authentication/verifying-requests-from-slack/](https://docs.slack.dev/authentication/verifying-requests-from-slack/): "The full signature is formed by prefixing the hex digest with v0=, to make 'v0=a2114d57b48eac39b9ad189dd8316235a7b4a8d21a10bd27519666489c69b503'."
- **Signed content:** The base string: the version v0, a colon, the value of X-Slack-Request-Timestamp, a colon, then the raw request body, i.e. v0:{timestamp}:{raw_body}
  Read 2026-10-20 from [docs.slack.dev/authentication/verifying-requests-from-slack/](https://docs.slack.dev/authentication/verifying-requests-from-slack/): "Concatenate the version number, the timestamp, and the request body together, using a colon ( : ) as a delimiter."
- **Header format:** Single signature, form v0=<64 hex chars>. The page says header names are meant to be case-insensitive, so do not assume letter case.
  Read 2026-10-20 from [docs.slack.dev/authentication/verifying-requests-from-slack/](https://docs.slack.dev/authentication/verifying-requests-from-slack/): "header names are meant to be case-insensitive, so the letter case should not be assumed"
- **Where the secret comes from:** App Signing Secret, in the app admin panel under Basic Info (Basic Information)
  Read 2026-10-20 from [docs.slack.dev/authentication/verifying-requests-from-slack/](https://docs.slack.dev/authentication/verifying-requests-from-slack/): "Grab your Slack Signing Secret, available in the app admin panel under Basic Info."
- **Secret scope:** Per app (Slack creates a unique string for your app)
  Read 2026-10-20 from [docs.slack.dev/authentication/verifying-requests-from-slack/](https://docs.slack.dev/authentication/verifying-requests-from-slack/): "Slack creates a unique string for your app and shares it with you."
- **Timestamp tolerance:** Five minutes: reject if the timestamp differs from local time by more than five minutes (the page's pseudocode uses 60 * 5 seconds)
  Read 2026-10-20 from [docs.slack.dev/authentication/verifying-requests-from-slack/](https://docs.slack.dev/authentication/verifying-requests-from-slack/): "In this example, we verify that the timestamp does not differ from local time by more than five minutes."
- **Secret rotation:** Regenerate button next to the Signing Secret in the admin panel. The page does not describe dual signatures or a grace period.
  Read 2026-10-20 from [docs.slack.dev/authentication/verifying-requests-from-slack/](https://docs.slack.dev/authentication/verifying-requests-from-slack/): "Regenerate your secret using the "Regenerate" button next to the Signing Secret in the admin panel."
- **Raw body:** Use the raw request body, before it has been deserialized from JSON or other forms.
  Read 2026-10-20 from [docs.slack.dev/authentication/verifying-requests-from-slack/](https://docs.slack.dev/authentication/verifying-requests-from-slack/): "Use the raw request body, without headers, before it has been deserialized from JSON or other forms"
- **Official helper (Node.js):** Bolt for JavaScript has built-in signing-secret verification (initialise with process.env.SLACK_SIGNING_SECRET). The page also shows createMessageAdapter(process.env.SLACK_SIGNING_SECRET) for interactions. No standalone verify function is shown.
  Read 2026-10-20 from [docs.slack.dev/authentication/verifying-requests-from-slack/](https://docs.slack.dev/authentication/verifying-requests-from-slack/): "const interactions = createMessageAdapter(process.env.SLACK_SIGNING_SECRET);"
- **Official helper (Python):** Bolt for Python has built-in signing-secret verification. No standalone verify function is shown.
  Read 2026-10-20 from [docs.slack.dev/authentication/verifying-requests-from-slack/](https://docs.slack.dev/authentication/verifying-requests-from-slack/): "Built-in support in Bolt for Python"
- **Official helper (.NET):** not stated by the provider (the page lists Bolt for JavaScript, Python and Java)
  Read 2026-10-20 from [docs.slack.dev/authentication/verifying-requests-from-slack/](https://docs.slack.dev/authentication/verifying-requests-from-slack/): "Built-in support in Bolt for Java"
- **Published example:**

  ```json
  {
    "note": "The page's worked example is a slash command (form-encoded body). Recomputed with HMAC-SHA256 during research: it matches.",
    "signing_secret": "8f742231b10e8888abcd99yyyzzz85a5",
    "timestamp": "1531420618",
    "body": "token=xyzz0WbapA4vBCDEFasx0q6G&team_id=T1DC2JH3J&team_domain=testteamnow&channel_id=G8PSS9T3V&channel_name=foobar&user_id=U2CERLKJA&user_name=roadrunner&command=%2Fwebhook-collect&text=&response_url=https%3A%2F%2Fhooks.slack.com%2Fcommands%2FT1DC2JH3J%2F397700885554%2F96rGlfmibIGlgcZRskXaIFfN&trigger_id=398738663015.47445629121.803a0bc887a14d10d2c447fce8b6703c",
    "signature": "v0=a2114d57b48eac39b9ad189dd8316235a7b4a8d21a10bd27519666489c69b503"
  }
  ```

  Read 2026-10-20 from [docs.slack.dev/authentication/verifying-requests-from-slack/](https://docs.slack.dev/authentication/verifying-requests-from-slack/): "In this example, the Signing Secret is 8f742231b10e8888abcd99yyyzzz85a5."

## Delivery

- **Method and content type:** Events API: HTTP POST with Content-Type application/json. Interactivity (buttons, shortcuts, modals): HTTP POST, application/x-www-form-urlencoded, with a payload parameter holding JSON.
  Read 2026-10-20 from [docs.slack.dev/apis/events-api/](https://docs.slack.dev/apis/events-api/): "we'll send an HTTP POST request to your request URL. The event will be in the Content-Type: application/json format"
- **Event name:** Outer envelope: top-level type (event_callback, or url_verification during setup). Event name: event.type inside the envelope.
  Read 2026-10-20 from [docs.slack.dev/apis/events-api/](https://docs.slack.dev/apis/events-api/): "Typically, that is event_callback. You may encounter url_verification during the configuration process."
- **Delivery or event id:** event_id, a string at the top level of the envelope (for example Ev123ABC456), with event_time in epoch seconds
  Read 2026-10-20 from [docs.slack.dev/apis/events-api/](https://docs.slack.dev/apis/events-api/): ""event_id" : "Ev123ABC456" , "event_time" : 1234567890"
- **Handshake:** url_verification: Slack POSTs JSON {token, challenge, type: url_verification}. Respond HTTP 200 with the challenge value, either as the raw challenge string, or as application/x-www-form-urlencoded challenge=..., or as JSON {"challenge": "..."}. The request URL must be confirmed before the form can be saved.
  Read 2026-10-20 from [docs.slack.dev/apis/events-api/using-http-request-urls/](https://docs.slack.dev/apis/events-api/using-http-request-urls/): "Once you receive the event, complete the sequence by responding with HTTP 200 and the challenge attribute value."
- **Events per request:** One event per request
  Read 2026-10-20 from [docs.slack.dev/apis/events-api/](https://docs.slack.dev/apis/events-api/): "Your request URL will receive a request for each event matching your subscriptions. One request, one event."
- **Interactive payload format:** application/x-www-form-urlencoded body with a payload field that must be parsed as JSON; every structure has a type field
  Read 2026-10-20 from [docs.slack.dev/interactivity/handling-user-interaction/](https://docs.slack.dev/interactivity/handling-user-interaction/): "They'll be sent to your specified Request URL in an HTTP POST request in the form application/x-www-form-urlencoded."
- **Interactive payload parse:** The body contains a payload parameter; parse it as JSON
  Read 2026-10-20 from [docs.slack.dev/interactivity/handling-user-interaction/](https://docs.slack.dev/interactivity/handling-user-interaction/): "The body of the request will contain a payload parameter; your app should parse this payload parameter as JSON."
- **Event type inner:** event.type, e.g. reaction_added, message.channels, team_join
  Read 2026-10-20 from [docs.slack.dev/apis/events-api/](https://docs.slack.dev/apis/events-api/): "The specific name of the event described by its adjacent fields."
- **Handshake payload:** {"token": "Jhj5dZrVaK7ZwHHjRyZWjbDl", "challenge": "3eZbrw1aBm2rZgRNFdxV2595E9CY3gmdALWMmHkvFXO7tYXAYM8P", "type": "url_verification"}
  Read 2026-10-20 from [docs.slack.dev/reference/events/url_verification/](https://docs.slack.dev/reference/events/url_verification/): ""challenge" : "3eZbrw1aBm2rZgRNFdxV2595E9CY3gmdALWMmHkvFXO7tYXAYM8P" , "type" : "url_verification""

## Responding and retries

- **Expected response:** Any HTTP 2xx for Events API requests; HTTP 200 OK for interaction payloads
  Read 2026-10-20 from [docs.slack.dev/apis/events-api/](https://docs.slack.dev/apis/events-api/): "Your app should respond to the event request with an HTTP 2xx within three seconds."
- **Response deadline:** 3 seconds: an Events API request not answered with a 2xx within three seconds counts as a failed attempt
  Read 2026-10-20 from [docs.slack.dev/apis/events-api/](https://docs.slack.dev/apis/events-api/): "Your app should respond to the event request with an HTTP 2xx within three seconds."
- **Retries:** Up to 3 retries: first nearly immediately, second after 1 minute, third and final after 5 minutes. Header x-slack-retry-num is 1, 2 or 3. Header x-slack-retry-reason is one of http_timeout, too_many_redirects (more than 2 redirects), ssl_error, unknown_error. Retries count against the failure limits. Optional Delayed Events setting adds hourly retries for 24 hours; by default an event more than two hours late is not delivered.
  Read 2026-10-20 from [docs.slack.dev/apis/events-api/](https://docs.slack.dev/apis/events-api/): "The first retry will be sent nearly immediately. The second retry will be attempted after 1 minute. The third and final retry will be sent after 5 minutes."
- **Disabling after failures:** Event subscriptions are temporarily disabled when failure conditions affect more than 95% of delivery attempts within 60 minutes. Apps receiving fewer than 1,000 events per hour are not auto-disabled. Re-enable via app management.
  Read 2026-10-20 from [docs.slack.dev/apis/events-api/](https://docs.slack.dev/apis/events-api/): "When your application enters any combination of these failure conditions for more than 95% of delivery attempts within 60 minutes, your application's event subscriptions will be temporarily disabled"
- **Ordering:** not stated by the provider (the page calls the Events API best-effort and says delivery can be delayed during incidents)
  Read 2026-10-20 from [docs.slack.dev/apis/events-api/](https://docs.slack.dev/apis/events-api/): "The Events API is a best-effort system, and event delivery could be delayed during incidents."
- **Duplicates:** Not stated as a guarantee either way. A retried event is sent again with x-slack-retry-num set to the attempt number.
  Read 2026-10-20 from [docs.slack.dev/apis/events-api/](https://docs.slack.dev/apis/events-api/): "With each retry attempt, you'll also be given a x-slack-retry-num HTTP header indicating the attempt number: 1, 2, or 3."
- **Interaction ack:** HTTP 200 OK within 3 seconds; otherwise the Slack user sees an error
  Read 2026-10-20 from [docs.slack.dev/interactivity/handling-user-interaction/](https://docs.slack.dev/interactivity/handling-user-interaction/): "your app must reply to the HTTP POST request with an HTTP 200 OK response. This must be sent within 3 seconds of receiving the payload."
- **Retry headers:** x-slack-retry-num (1, 2 or 3) and x-slack-retry-reason (http_timeout, too_many_redirects, ssl_error, unknown_error)
  Read 2026-10-20 from [docs.slack.dev/apis/events-api/](https://docs.slack.dev/apis/events-api/): "With each retry attempt, you'll also be given a x-slack-retry-num HTTP header indicating the attempt number: 1, 2, or 3."
- **Retry opt out:** Send header x-slack-no-retry: 1 on a non-200 response to stop redelivery of that specific event
  Read 2026-10-20 from [docs.slack.dev/apis/events-api/](https://docs.slack.dev/apis/events-api/): "x-slack-no-retry: 1"
- **Delayed events:** Optional Delayed Events setting: three quick retries followed by hourly retries for 24 hours; default drops events more than two hours late
  Read 2026-10-20 from [docs.slack.dev/apis/events-api/](https://docs.slack.dev/apis/events-api/): "Enable the Delayed Events feature for Slack to follow those three retries with hourly retries for 24 hours."
- **Disabling threshold note:** Keep a success response rate of at least 5% of events per 60 minutes; apps below 1,000 events per hour are exempt
  Read 2026-10-20 from [docs.slack.dev/apis/events-api/](https://docs.slack.dev/apis/events-api/): "However, apps receiving less than 1,000 events per hour will not be automatically disabled."

## Events

Full list: https://docs.slack.dev/reference/events/

- **`message`:** A message was posted in a channel the app can see (message.channels etc. variants exist)
  Read 2026-10-20 from [docs.slack.dev/reference/events/](https://docs.slack.dev/reference/events/): "A message was sent to a channel"
- **`app_mention`:** A message mentioned the app
  Read 2026-10-20 from [docs.slack.dev/reference/events/](https://docs.slack.dev/reference/events/): "Subscribe to only the message events that mention your app or bot"
- **`app_home_opened`:** A user opened the app's Home tab
  Read 2026-10-20 from [docs.slack.dev/reference/events/](https://docs.slack.dev/reference/events/): "User clicked into your App Home"
- **`member_joined_channel`:** A user joined a channel
  Read 2026-10-20 from [docs.slack.dev/reference/events/](https://docs.slack.dev/reference/events/): "A user joined a public channel, private channel or MPDM"
- **`reaction_added`:** An emoji reaction was added to an item
  Read 2026-10-20 from [docs.slack.dev/reference/events/](https://docs.slack.dev/reference/events/): "A member has added an emoji reaction to an item"
- **`channel_created`:** A channel was created
  Read 2026-10-20 from [docs.slack.dev/reference/events/](https://docs.slack.dev/reference/events/): "A channel was created"
- **`team_join`:** A new member joined the workspace
  Read 2026-10-20 from [docs.slack.dev/reference/events/](https://docs.slack.dev/reference/events/): "A new member has joined"
- **`url_verification`:** Setup-time ownership challenge, not a real event
  Read 2026-10-20 from [docs.slack.dev/reference/events/](https://docs.slack.dev/reference/events/): "Verifies ownership of an Events API Request URL"

## Setup and testing

- **Where the URL goes:** App settings, Event Subscriptions (toggle on), then the Request URL; the URL must pass the url_verification challenge before the form saves. Interactivity has its own Request URL.
  Read 2026-10-20 from [docs.slack.dev/apis/events-api/](https://docs.slack.dev/apis/events-api/): "find the Event Subscriptions setting and use the toggle to turn it on."
- **Test tools:** not stated by the provider (the pages read mention only the Retry button for URL verification)
  Read 2026-10-20 from [docs.slack.dev/apis/events-api/using-http-request-urls/](https://docs.slack.dev/apis/events-api/using-http-request-urls/): "use the Retry button to attempt verification again."
- **Source IP addresses:** not stated by the provider
  Checked 2026-10-20 at [docs.slack.dev/apis/events-api/](https://docs.slack.dev/apis/events-api/).
- **Url confirmation:** Request URL must be confirmed before saving; a Retry button re-attempts verification after a timeout; request URLs are case-sensitive
  Read 2026-10-20 from [docs.slack.dev/apis/events-api/using-http-request-urls/](https://docs.slack.dev/apis/events-api/using-http-request-urls/): "Your Event request URL must be confirmed before saving this form."

## Pitfalls the provider warns about

- **1:** Event deliveries are capped at 30,000 per workspace per app per 60 minutes; beyond that app_rate_limited events are sent every minute.
  Read 2026-10-20 from [docs.slack.dev/apis/events-api/](https://docs.slack.dev/apis/events-api/): "Event deliveries currently max out at 30,000 per workspace/team per app per 60 minutes."
- **2:** The top-level token field is deprecated; verify with the signing secret instead.
  Read 2026-10-20 from [docs.slack.dev/apis/events-api/](https://docs.slack.dev/apis/events-api/): "Instead of using the token, you should rely on using signed secrets to verify requests from Slack."
- **3:** Compare signatures with a constant-time HMAC compare, not direct string equality.
  Read 2026-10-20 from [docs.slack.dev/authentication/verifying-requests-from-slack/](https://docs.slack.dev/authentication/verifying-requests-from-slack/): "use an hmac compare function instead of directly comparing the signatures for equality."
- **4:** The Events API tolerates added fields: expect extra or conditionally present fields.
  Read 2026-10-20 from [docs.slack.dev/apis/events-api/](https://docs.slack.dev/apis/events-api/): "to expect additional fields you haven't encountered before or fields that are only conditionally present."
- **5:** If one event is visible to several installed users, Slack sends it once with a single user in authorizations.
  Read 2026-10-20 from [docs.slack.dev/apis/events-api/](https://docs.slack.dev/apis/events-api/): "we will send one event and include one user to whom this event is "visible" in the authorizations.user_id field."

## In WebhookVault

What WebhookVault does with Slack requests, read from its provider catalogue on 2026-10-20. These are facts about WebhookVault, not about Slack.

- **Signature header it reads:** `X-Slack-Signature`
- **Checks the signature:** yes (HMAC-SHA256 hex over "v0:timestamp:body" with X-Slack-Request-Timestamp, prefixed v0=, 5 minute tolerance)
- **Secret field label:** Signing secret
- **Where it finds the event name:** body `event.type`, then body `type`
- **Where the capture URL goes in Slack:** api.slack.com > Your app > Event Subscriptions > Request URL
