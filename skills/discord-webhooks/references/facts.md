# Discord webhook facts

Generated from `data/providers/discord.json` by `tools/provider-facts.mjs`; change the data and regenerate, never this file.
Every fact was read from Discord's own pages on the date shown, with the sentence it came from. Quotes are verbatim except that long dashes are written as hyphens. "not stated by the provider" means the pages read did not say; it does not mean there is no rule.

## Contents

- [Signature](#signature)
- [Delivery](#delivery)
- [Responding and retries](#responding-and-retries)
- [Events](#events)
- [Setup and testing](#setup-and-testing)
- [Interactions endpoint](#interactions-endpoint)
- [Pitfalls the provider warns about](#pitfalls-the-provider-warns-about)
- [In WebhookVault](#in-webhookvault)

## Signature

- **Signature header:** X-Signature-Ed25519; X-Signature-Timestamp
  Read 2026-10-20 from [discord.com/developers/docs/interactions/overview](https://discord.com/developers/docs/interactions/overview): "X-Signature-Ed25519 as a signature"
- **Scheme:** Ed25519 detached signature, hex encoded, verified with the application public key (hex encoded); the docs example uses nacl.sign.detached.verify with hex-decoded signature and public key
  Read 2026-10-20 from [discord.com/developers/docs/interactions/overview](https://discord.com/developers/docs/interactions/overview): "nacl.sign.detached.verify( Buffer.from(timestamp + body), Buffer.from(signature, "hex"), Buffer.from(PUBLIC_KEY, "hex") )"
- **Signed content:** The value of X-Signature-Timestamp concatenated directly with the raw request body (timestamp + body, no separator)
  Read 2026-10-20 from [discord.com/developers/docs/interactions/overview](https://discord.com/developers/docs/interactions/overview): "Buffer.from(timestamp + body)"
- **Header format:** X-Signature-Ed25519 carries the signature as a hex string; X-Signature-Timestamp carries the timestamp as a string. One signature, no prefixes or key=value pairs (inferred from the docs code examples, which hex-decode the whole header value)
  Read 2026-10-20 from [discord.com/developers/docs/interactions/overview](https://discord.com/developers/docs/interactions/overview): "Buffer.from(signature, "hex")"
- **Where the secret comes from:** The application's public key, found on the application in the Developer Portal
  Read 2026-10-20 from [discord.com/developers/docs/interactions/overview](https://discord.com/developers/docs/interactions/overview): "Your public key can be found on your application in the Developer Portal"
- **Secret scope:** Per application (one public key per Discord application)
  Read 2026-10-20 from [discord.com/developers/docs/interactions/overview](https://discord.com/developers/docs/interactions/overview): "Your public key can be found on your application in the Developer Portal"
- **Timestamp tolerance:** not stated by the provider
  Checked 2026-10-20 at [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events).
- **Secret rotation:** not stated by the provider
  Checked 2026-10-20 at [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events).
- **Raw body:** The docs JavaScript example uses req.rawBody and notes it is expected to be a string, not raw bytes
  Read 2026-10-20 from [discord.com/developers/docs/interactions/overview](https://discord.com/developers/docs/interactions/overview): "const body = req.rawBody; // rawBody is expected to be a string, not raw bytes"
- **On invalid signature:** Respond 401
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "If the signature fails validation, your app should respond with a 401 error code."
- **Official helper (Node.js):** verifyKey(rawBody, signature, timestamp, clientPublicKey), or verifyWebhookEventMiddleware(clientPublicKey), from the discord-interactions npm package (github.com/discord/discord-interactions-js)
  Read 2026-10-20 from [github.com/discord/discord-interactions-js](https://github.com/discord/discord-interactions-js): "If you're using an express-like API, you can simplify things by using the `verifyWebhookEventMiddleware`."
- **Official helper (Python):** verify_key(raw_body, signature, timestamp, client_public_key) from the discord-interactions PyPI package; its README describes it for signed payloads POSTed to a webhook endpoint and does not mention Webhook Events by name
  Read 2026-10-20 from [github.com/discord/discord-interactions-python](https://github.com/discord/discord-interactions-python): "Verify a signed payload POSTed to your webhook endpoint."
- **Official helper (.NET):** not stated by the provider
  Checked 2026-10-20 at [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events).

## Delivery

- **Method and content type:** POST (stated for the PING); request content type not stated
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "Discord will send a POST request with a PING payload with a type: 0 to your endpoint."
- **Event name:** JSON path event.type (string such as APPLICATION_AUTHORIZED); the outer `type` is the webhook type (0 PING, 1 event)
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "The “Value” column corresponds to the event’s type field value in the event body object."
- **Delivery or event id:** not stated by the provider (no delivery-id header or envelope field is documented; `data.id` on entitlement events is the entitlement ID, not a delivery ID)
  Checked 2026-10-20 at [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events).
- **Handshake:** When the Webhook Events URL is added, Discord POSTs a PING payload with `type: 0`; the app must acknowledge with HTTP 204 and an empty body (plus a valid Content-Type) and must validate the signature headers, otherwise the URL is not validated
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "Your app is expected to acknowledge the request by returning a 204 response with an empty body."
- **Events per request:** One event per request (the envelope carries a single `event` object)
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "Webhook events are wrapped in an outer payload, with an inner event object."
- **Envelope:** { version: 1, application_id: <snowflake>, type: 0|1, event: { type: <string>, timestamp: <ISO8601 string>, data: <object> } }; `event` is absent on PING
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "Webhook events are wrapped in an outer payload, with an inner event object."
- **Envelope version:** 1
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "Version scheme for the webhook event. Currently always 1"
- **Webhook type:** 0 = PING, 1 = Event
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "Type of webhook, either 0 for PING or 1 for webhook events"

## Responding and retries

- **Expected response:** HTTP 204 with no body
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "your app should respond with a 204 status code with no body within 3 seconds"
- **Response deadline:** 3 seconds
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "your app should respond with a 204 status code with no body within 3 seconds"
- **Retries:** If the app does not respond, Discord retries several times with exponential backoff for up to 10 minutes. The number of attempts is not stated.
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "Discord will retry sending it several times using exponential backoff for up to 10 minutes."
- **Disabling after failures:** If the app fails to respond too often, Discord stops sending webhook events and notifies by email. The threshold is not stated. Separately, failing the routine invalid-signature security checks removes the Webhook Events URL and alerts via email and System DM.
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "If your app fails to respond too often, Discord will stop sending you webhook events and notify you via email."
- **Ordering:** Not guaranteed in order and not realtime
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "events sent over webhooks are not realtime or guaranteed to be in order."
- **Duplicates:** not stated by the provider (retries imply a repeat can arrive if the 204 is late, but the page does not say so)
  Checked 2026-10-20 at [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events).
- **Security check removal:** Routine automated checks send invalid signatures on purpose; failing them removes the URL
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "If you fail the validation, we will remove your Webhook Events URL and alert you via email and System DM."

## Events

Full list: https://discord.com/developers/docs/events/webhook-events#event-types

- **Other listed types:** ENTITLEMENT_UPDATE; ENTITLEMENT_DELETE; LOBBY_MESSAGE_UPDATE; LOBBY_MESSAGE_DELETE; GAME_DIRECT_MESSAGE_UPDATE; GAME_DIRECT_MESSAGE_DELETE
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "Sent when a message is updated in a lobby"

- **`APPLICATION_AUTHORIZED`:** App added to a server or user account; data has user, scopes, optional guild and integration_type
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "APPLICATION_AUTHORIZED is sent when the app is added to a server or user account."
- **`APPLICATION_DEAUTHORIZED`:** A user deauthorized the app; data has the user
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "APPLICATION_DEAUTHORIZED is sent when the app is deauthorized by a user."
- **`ENTITLEMENT_CREATE`:** A user purchased or was granted one of the app's SKUs; data is an entitlement object
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "ENTITLEMENT_CREATE is sent when an entitlement is created when a user purchases or is otherwise granted one of your app’s SKUs."
- **`ENTITLEMENT_UPDATE`:** An entitlement changed; data is an entitlement object
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "ENTITLEMENT_UPDATE is sent when an entitlement is updated."
- **`ENTITLEMENT_DELETE`:** An entitlement was deleted; data is an entitlement object
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "ENTITLEMENT_DELETE is sent when an entitlement is deleted."
- **`QUEST_USER_ENROLLMENT`:** User added to a Quest; documented but not receivable by apps at present
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "This event cannot be received by apps at this time."
- **`LOBBY_MESSAGE_CREATE`:** Message created in a Social SDK lobby; data is a lobby message object
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "LOBBY_MESSAGE_CREATE is sent when a message is created in a lobby."
- **`GAME_DIRECT_MESSAGE_CREATE`:** Direct message created during an active Social SDK session
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "Sent when a direct message is created during an active Social SDK session"

## Setup and testing

- **Where the URL goes:** Developer Portal: the app's Webhooks page (left sidebar), Endpoint field, then toggle Events on and select events, then Save Changes. Via API: Edit Current Application.
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "Under Endpoint, add a public URL that is set up to receive and acknowledge webhook events."
- **Test tools:** not stated by the provider (the PING sent when the URL is saved is the only documented probe)
  Checked 2026-10-20 at [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events).
- **Source IP addresses:** not stated by the provider
  Checked 2026-10-20 at [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events).
- **Api alternative:** Edit Current Application
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "If you prefer to use the API, you can call Edit Current Application."
- **Gateway alternative:** A Webhook Events URL is not needed if the app uses Gateway events
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "If your app is using Gateway events, you don’t need to configure a Webhook Events URL."

## Interactions endpoint

- **Method and content type:** POST; request content type not stated on these pages (body is the Interaction object JSON)
  Read 2026-10-20 from [discord.com/developers/docs/interactions/overview](https://discord.com/developers/docs/interactions/overview): "Discord will send a POST request with a PING payload with a type: 1 to your endpoint."
- **Event name:** JSON body field `type` (integer interaction type): PING=1, APPLICATION_COMMAND=2, MESSAGE_COMPONENT=3, APPLICATION_COMMAND_AUTOCOMPLETE=4, MODAL_SUBMIT=5. There is no event-name header.
  Read 2026-10-20 from [discord.com/developers/docs/interactions/receiving-and-responding](https://discord.com/developers/docs/interactions/receiving-and-responding): "PING1 APPLICATION_COMMAND2 MESSAGE_COMPONENT3 APPLICATION_COMMAND_AUTOCOMPLETE4 MODAL_SUBMIT5"
- **Delivery or event id:** Body field `id` (snowflake, ID of the interaction). No delivery-id header is documented.
  Read 2026-10-20 from [discord.com/developers/docs/interactions/receiving-and-responding](https://discord.com/developers/docs/interactions/receiving-and-responding): "idsnowflakeID of the interaction"
- **Handshake:** When the Interactions Endpoint URL is saved, Discord POSTs a PING with `type: 1`; the app must return HTTP 200 with a PONG body `{"type": 1}` and a valid Content-Type, and must also validate the signature headers. If either is incomplete the URL is not validated.
  Read 2026-10-20 from [discord.com/developers/docs/interactions/overview](https://discord.com/developers/docs/interactions/overview): "returning a 200 response with a PONG payload (which has the same type: 1)"
- **Events per request:** One interaction object per request (the body is a single Interaction object)
  Read 2026-10-20 from [discord.com/developers/docs/interactions/receiving-and-responding](https://discord.com/developers/docs/interactions/receiving-and-responding): "Interaction Structure"
- **Expected response:** HTTP 200 with a JSON Interaction Response object (`type` and optional `data`); for PING, 200 with `{"type": 1}`
  Read 2026-10-20 from [discord.com/developers/docs/interactions/receiving-and-responding](https://discord.com/developers/docs/interactions/receiving-and-responding): "respond with a 200 status code (if everything went well), as well as specifying a type and data"
- **Response deadline:** 3 seconds for the initial response; if exceeded the interaction token is invalidated
  Read 2026-10-20 from [discord.com/developers/docs/interactions/receiving-and-responding](https://discord.com/developers/docs/interactions/receiving-and-responding): "you must send an initial response within 3 seconds of receiving the event. If the 3 second deadline is exceeded, the token will be invalidated."
- **Token lifetime:** 15 minutes (interaction token, usable for followup messages and edits)
  Read 2026-10-20 from [discord.com/developers/docs/interactions/receiving-and-responding](https://discord.com/developers/docs/interactions/receiving-and-responding): "Interaction tokens are valid for 15 minutes"
- **Retries:** not stated by the provider
  Checked 2026-10-20 at [discord.com/developers/docs/interactions/receiving-and-responding](https://discord.com/developers/docs/interactions/receiving-and-responding).
- **Disabling after failures:** Discord runs routine automated security checks against the endpoint, including purposefully sending invalid signatures; failing them removes the Interactions Endpoint URL and alerts via email and System DM. Failure behaviour for ordinary non-responses is not stated.
  Read 2026-10-20 from [discord.com/developers/docs/interactions/overview](https://discord.com/developers/docs/interactions/overview): "purposefully sending you invalid signatures. If you fail the validation, we will remove your interactions URL and alert you via email and System DM."
- **Ordering:** not stated by the provider
  Checked 2026-10-20 at [discord.com/developers/docs/interactions/receiving-and-responding](https://discord.com/developers/docs/interactions/receiving-and-responding).
- **Duplicates:** not stated by the provider
  Checked 2026-10-20 at [discord.com/developers/docs/interactions/receiving-and-responding](https://discord.com/developers/docs/interactions/receiving-and-responding).
- **Where the URL goes:** Developer Portal, the application's General Information page, in the Interactive Endpoint URL field
  Read 2026-10-20 from [discord.com/developers/docs/interactions/overview](https://discord.com/developers/docs/interactions/overview): "On the General Information page, look for the Interactive Endpoint URL field."
- **Default transport:** Without an endpoint URL the app receives interactions over the Gateway; HTTP delivery is opt-in
  Read 2026-10-20 from [discord.com/developers/docs/interactions/overview](https://discord.com/developers/docs/interactions/overview): "By default your app will receive interactions via a Gateway connection, but you can opt-in to HTTP-based interactions"
- **Test tools:** not stated by the provider (the PING sent on saving the URL is the only documented probe)
  Checked 2026-10-20 at [discord.com/developers/docs/interactions/overview](https://discord.com/developers/docs/interactions/overview).
- **Source IP addresses:** not stated by the provider
  Checked 2026-10-20 at [discord.com/developers/docs/interactions/overview](https://discord.com/developers/docs/interactions/overview).

Interaction types:

- **`PING (type 1)`:** Handshake sent when the endpoint URL is saved and at other validation times; answer 200 with {type: 1}
  Read 2026-10-20 from [discord.com/developers/docs/interactions/overview](https://discord.com/developers/docs/interactions/overview): "returning a 200 response with a PONG payload (which has the same type: 1)"
- **`PONG (callback type 1)`:** The response value that acknowledges a PING
  Read 2026-10-20 from [discord.com/developers/docs/interactions/receiving-and-responding](https://discord.com/developers/docs/interactions/receiving-and-responding): "PONG1ACK a Ping"
- **`CHANNEL_MESSAGE_WITH_SOURCE (callback type 4)`:** Respond to an interaction with a message
  Read 2026-10-20 from [discord.com/developers/docs/interactions/receiving-and-responding](https://discord.com/developers/docs/interactions/receiving-and-responding): "CHANNEL_MESSAGE_WITH_SOURCE4Respond to an interaction with a message"
- **`DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE (callback type 5)`:** Acknowledge now, edit the response later; the user sees a loading state
  Read 2026-10-20 from [discord.com/developers/docs/interactions/receiving-and-responding](https://discord.com/developers/docs/interactions/receiving-and-responding): "ACK an interaction and edit a response later, the user sees a loading state"


Pitfalls:

- **1:** Both the PING answer and the signature validation must be in place before the URL will save; Discord also sends deliberately invalid signatures later and expects 401
  Read 2026-10-20 from [discord.com/developers/docs/interactions/overview](https://discord.com/developers/docs/interactions/overview): "If either of these are not complete, your Interactions Endpoint URL will not be validated."
- **2:** The PING response needs a valid Content-Type
  Read 2026-10-20 from [discord.com/developers/docs/interactions/overview](https://discord.com/developers/docs/interactions/overview): "You must provide a valid Content-Type when responding to PINGs."
- **3:** The signed message is the timestamp header followed by the body; the docs example treats rawBody as a string, not bytes
  Read 2026-10-20 from [discord.com/developers/docs/interactions/overview](https://discord.com/developers/docs/interactions/overview): "rawBody is expected to be a string, not raw bytes"
- **4:** Missing the 3 second initial-response deadline invalidates the token
  Read 2026-10-20 from [discord.com/developers/docs/interactions/receiving-and-responding](https://discord.com/developers/docs/interactions/receiving-and-responding): "If the 3 second deadline is exceeded, the token will be invalidated."


Notes from reading these pages (our words, not the provider's):

- Interactions are not named events; they are typed by the integer `type` field. Response callback types: PONG=1, CHANNEL_MESSAGE_WITH_SOURCE=4, DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE=5 (others exist on the page).
- Discord has two HTTP mechanisms with the same signature: the Interactions Endpoint URL (slash commands, buttons; answered with an interaction response) and Webhook Events (app events such as APPLICATION_AUTHORIZED; answered 204). The standard sections above are Webhook Events; the Interactions endpoint section covers the other. The Webhook Events page does not restate the signature algorithm and refers to the Interactions documentation, so the signature facts come from there.

## Pitfalls the provider warns about

- **1:** The PING answer here differs from interactions: 204 with an empty body, not 200 with {type: 1}
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "returning a 204 response with an empty body."
- **2:** Real events must also be answered 204, no body, within 3 seconds
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "your app should respond with a 204 status code with no body within 3 seconds"
- **3:** The PING response needs a valid Content-Type
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "You must provide a valid Content-Type when responding to PINGs."
- **4:** Webhook events are not realtime and not ordered
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "events sent over webhooks are not realtime or guaranteed to be in order."
- **5:** Discord sends deliberately invalid signatures as routine checks and removes the URL if they are accepted
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "including purposefully sending you invalid signatures."
- **6:** For Social SDK apps, APPLICATION_DEAUTHORIZED is the only out-of-game signal that a user's link state changed; missing it makes the next token use fail
  Read 2026-10-20 from [discord.com/developers/docs/events/webhook-events](https://discord.com/developers/docs/events/webhook-events): "if you miss the webhook, the next token use will fail"

## In WebhookVault

What WebhookVault does with Discord requests, read from its provider catalogue on 2026-10-20. These are facts about WebhookVault, not about Discord.

- **Signature header it reads:** `X-Signature-Ed25519`
- **Checks the signature:** yes (Ed25519 over timestamp + body from X-Signature-Ed25519 and X-Signature-Timestamp, verified with the application public key)
- **Secret field label:** Discord application public key (hex)
- **Where it finds the event name:** body `event.type`
- **Where the capture URL goes in Discord:** Discord saves an Interactions Endpoint URL only after its signed PING check, which a capture URL cannot answer. Register your own handler there and have it relay each interaction to this URL (the Discord guide: https://webhookvault.net/providers/discord/)
