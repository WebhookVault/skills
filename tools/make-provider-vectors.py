"""Writes skills/<slug>-webhooks/examples/fixtures/vectors.json for each provider skill: signed requests
and the answer a correct receiver gives, computed with the openssl command line and never by the
example code under test. Each provider's Node.js, Python and C# examples run every case in that file,
so the three languages are held to the same answers by something outside all of them.

    python tools/make-provider-vectors.py              every provider below
    python tools/make-provider-vectors.py slack twilio only these

Needs openssl 3 on PATH. Every secret and key is a test value made for these vectors; key-pair
schemes use keys generated on each run, and only the public halves and signatures are written.
Where a provider's docs print a worked example, it is added as a case with its source and read date.

Case fields: name, now (the receiver's clock, unix seconds), method, url, headers, body (the exact
text sent), and expect: status, plus type and id (the event name and the id to deduplicate on) when
the request is accepted, reply when the receiver must answer with content, events for batches, and
verifyOnly cases that check the signature function alone.
"""

import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zlib
from urllib.parse import quote_plus, urlencode

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOW = 1760000000
NOTE = "test values only"


def openssl(args, data=b""):
    return subprocess.run(["openssl", *args], input=data, capture_output=True, check=True).stdout


def hmac(algo, key, data):
    """HMAC by openssl, the key passed as hex so any byte works."""
    if isinstance(key, str):
        key = key.encode()
    return openssl(["dgst", f"-{algo}", "-mac", "HMAC", "-macopt", f"hexkey:{key.hex()}", "-binary"], data)


def b64(b):
    return base64.b64encode(b).decode()


def compact(obj):
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


def case(name, body, expect, headers=None, method="POST", url=None, now=NOW, **extra):
    c = {"name": name, "now": now, "method": method}
    if url:
        c["url"] = url
    c["headers"] = headers or {}
    c["body"] = body
    c["expect"] = expect
    c.update(extra)
    c["note"] = NOTE
    return c


def write(slug, config, cases, published=()):
    path = os.path.join(ROOT, "skills", f"{slug}-webhooks", "examples", "fixtures", "vectors.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    version = openssl(["version"]).decode().strip().split(" (")[0]
    about = (f"Signed {slug} webhook requests and the answers a correct receiver gives. Made by "
             f"tools/make-provider-vectors.py with {version}; never by the code under test. Test values only.")
    # One case per line, so each line that carries a test secret also says it is a test value.
    text = "\n".join([
        "{",
        f'"about": {json.dumps(about)},',
        f'"config": {json.dumps({**config, "note": NOTE}, ensure_ascii=False)},',
        '"cases": [',
        ",\n".join(json.dumps(c, ensure_ascii=False) for c in [*cases, *published]),
        "]",
        "}",
    ]) + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"{slug}: {len(cases) + len(published)} cases -> {os.path.relpath(path, ROOT)}")


# ---- Slack -------------------------------------------------------------------------------------
# v0=hex(HMAC-SHA256(signing secret, "v0:" + timestamp + ":" + raw body)), timestamp in
# X-Slack-Request-Timestamp, five minutes either way (data/providers/slack.json).

def slack():
    secret = "test-slack-signing-secret"
    tol = 300

    def signed(body, ts=NOW - 10, key=secret, extra=None):
        mac = hmac("sha256", key, f"v0:{ts}:".encode() + body.encode())
        h = {"Content-Type": "application/json", "X-Slack-Request-Timestamp": str(ts), "X-Slack-Signature": "v0=" + mac.hex()}
        h.update(extra or {})
        return h

    event = compact({"token": "test-deprecated-token", "team_id": "T0TEST", "api_app_id": "A0TEST", "type": "event_callback",
                     "event_id": "Ev0TEST0001", "event_time": NOW - 12,
                     "event": {"type": "app_mention", "user": "U0TEST", "text": "<@U0APP> hello", "ts": "1760000000.000100", "channel": "C0TEST"}})
    challenge = compact({"token": "test-deprecated-token", "challenge": "test-challenge-3eZbrw1aBm2rZgRN", "type": "url_verification"})
    respaced = event.replace(",", ", ")
    interaction = compact({"type": "block_actions", "trigger_id": "123.456.test", "user": {"id": "U0TEST"},
                           "actions": [{"action_id": "approve", "type": "button", "value": "ok"}]})
    form = "payload=" + quote_plus(interaction)
    accepted = {"status": 200, "type": "app_mention", "id": "Ev0TEST0001"}
    cases = [
        case("event", event, accepted, signed(event)),
        case("retry of the same event", event, accepted, signed(event, extra={"X-Slack-Retry-Num": "1", "X-Slack-Retry-Reason": "http_timeout"})),
        case("url verification answered with the challenge", challenge,
             {"status": 200, "type": "url_verification", "id": None, "reply": "test-challenge-3eZbrw1aBm2rZgRN"}, signed(challenge)),
        case("url verification with a bad signature is refused", challenge, {"status": 401}, signed(challenge, key="test-wrong-secret")),
        case("interaction payload (form encoded)", form, {"status": 200, "type": "block_actions", "id": None},
             {**signed(form), "Content-Type": "application/x-www-form-urlencoded"}),
        case("tampered body", event.replace("hello", "hullo"), {"status": 401}, signed(event)),
        case("wrong secret", event, {"status": 401}, signed(event, key="test-wrong-secret")),
        case("re-serialised JSON", respaced, {"status": 401}, signed(event)),
        case("timestamp too old", event, {"status": 401}, signed(event, ts=NOW - tol - 1)),
        case("timestamp too far ahead", event, {"status": 401}, signed(event, ts=NOW + tol + 1)),
        case("timestamp at the edge", event, accepted, signed(event, ts=NOW - tol)),
        case("missing signature", event, {"status": 401}, {k: v for k, v in signed(event).items() if k != "X-Slack-Signature"}),
        case("missing timestamp", event, {"status": 401}, {k: v for k, v in signed(event).items() if k != "X-Slack-Request-Timestamp"}),
        case("malformed JSON with a valid signature", "{not json", {"status": 400}, signed("{not json")),
    ]
    # The worked example on Slack's "Verifying requests from Slack" page (a slash command).
    pv = json.load(open(os.path.join(ROOT, "data", "providers", "slack.json"), encoding="utf-8"))["signature"]["published_test_vector"]
    v = pv["value"]
    published = [case("published example (Slack docs)", v["body"], {"status": 200, "verified": True},
                      {"Content-Type": "application/x-www-form-urlencoded", "X-Slack-Request-Timestamp": v["timestamp"], "X-Slack-Signature": v["signature"]},
                      now=int(v["timestamp"]), verifyOnly=True, secret=v["signing_secret"], source=pv["source_url"], read=pv["read"])]
    write("slack", {"secret": secret, "toleranceSeconds": tol}, cases, published)


# ---- Twilio ------------------------------------------------------------------------------------
# Base64(HMAC-SHA1(auth token, URL + each POST parameter name and value, sorted by name)); for a JSON
# body the URL carries bodySHA256 (hex SHA-256 of the body) and no parameters are appended
# (data/providers/twilio.json).

def twilio():
    token = "test-twilio-auth-token"
    url = "https://example.test/twilio/status?tenant=7"
    params = {"AccountSid": "AC0test", "MessageSid": "SM0test0001", "MessageStatus": "delivered", "SmsStatus": "delivered",
              "To": "+15550001111", "From": "+15550002222", "ApiVersion": "2010-04-01"}

    def sign(u, p, key=token):
        s = u + "".join(k + p[k] for k in sorted(p))
        return b64(hmac("sha1", key, s.encode("utf-8")))

    def form(p):
        return urlencode(p)

    ctype = {"Content-Type": "application/x-www-form-urlencoded"}
    accepted = {"status": 200, "type": "delivered", "id": "SM0test0001"}
    extra = {**params, "ErrorCode": "", "Body": "Café & more + ok"}
    tampered = {**params, "MessageStatus": "failed"}
    json_body = compact({"CallSid": "CA0test0001", "CallStatus": "completed"})
    json_url = "https://example.test/twilio/json?bodySHA256=" + hashlib.sha256(json_body.encode()).hexdigest()
    jctype = {"Content-Type": "application/json"}
    cases = [
        case("status callback", form(params), accepted, {**ctype, "X-Twilio-Signature": sign(url, params)}, url=url),
        case("a parameter the receiver does not use is still signed", form(extra), accepted, {**ctype, "X-Twilio-Signature": sign(url, extra)}, url=url),
        case("retry carries the idempotency token", form(params), accepted,
             {**ctype, "X-Twilio-Signature": sign(url, params), "I-Twilio-Idempotency-Token": "test-idem-1"}, url=url),
        case("tampered parameter", form(tampered), {"status": 401}, {**ctype, "X-Twilio-Signature": sign(url, params)}, url=url),
        case("wrong auth token", form(params), {"status": 401}, {**ctype, "X-Twilio-Signature": sign(url, params, "test-wrong-token")}, url=url),
        case("URL the receiver sees differs from the one Twilio signed (http behind a proxy)", form(params), {"status": 401},
             {**ctype, "X-Twilio-Signature": sign(url, params)}, url=url.replace("https:", "http:")),
        case("trailing slash added by the server", form(params), {"status": 401},
             {**ctype, "X-Twilio-Signature": sign(url, params)}, url=url.replace("/status?", "/status/?")),
        case("missing signature", form(params), {"status": 401}, ctype, url=url),
        case("JSON body with bodySHA256", json_body, {"status": 200, "type": "completed", "id": "CA0test0001"},
             {**jctype, "X-Twilio-Signature": sign(json_url, {})}, url=json_url),
        case("JSON body changed after signing", json_body.replace("completed", "failed"), {"status": 401},
             {**jctype, "X-Twilio-Signature": sign(json_url, {})}, url=json_url),
        case("JSON body without bodySHA256 in the URL", json_body, {"status": 401},
             {**jctype, "X-Twilio-Signature": sign("https://example.test/twilio/json", {})}, url="https://example.test/twilio/json"),
    ]
    pv = json.load(open(os.path.join(ROOT, "data", "providers", "twilio.json"), encoding="utf-8"))["signature"]["published_test_vector"]
    v = pv["value"]
    pparams = dict(p.strip().split("=", 1) for p in v["post_params"].split(","))
    published = [case("published example (Twilio docs)", form(pparams), {"status": 200, "verified": True},
                      {**ctype, "X-Twilio-Signature": v["signature"]}, url=v["url"], verifyOnly=True,
                      secret=v["auth_token"], source=pv["source_url"], read=pv["read"])]
    write("twilio", {"secret": token}, cases, published)


# ---- SendGrid ----------------------------------------------------------------------------------
# ECDSA (P-256 key, SHA-256) over the timestamp header value followed by the raw body; signature is
# base64 DER; the public key is the base64 DER SubjectPublicKeyInfo shown in the settings
# (data/providers/sendgrid.json). Events arrive as a JSON array.

def sendgrid():
    with tempfile.TemporaryDirectory() as tmp:
        keys = []
        for name in ("key", "other"):
            pem = os.path.join(tmp, f"{name}.pem")
            openssl(["genpkey", "-algorithm", "EC", "-pkeyopt", "ec_paramgen_curve:P-256", "-out", pem])
            keys.append(pem)
        public = b64(openssl(["pkey", "-in", keys[0], "-pubout", "-outform", "DER"]))

        def sign(body, ts=NOW - 20, key=keys[0]):
            msg = os.path.join(tmp, "msg.bin")
            with open(msg, "wb") as f:
                f.write(str(ts).encode() + body.encode("utf-8"))
            sig = b64(openssl(["dgst", "-sha256", "-sign", key, msg]))
            return {"Content-Type": "application/json", "X-Twilio-Email-Event-Webhook-Signature": sig,
                    "X-Twilio-Email-Event-Webhook-Timestamp": str(ts)}

        events = [
            {"email": "test@example.test", "timestamp": NOW - 40, "event": "processed", "sg_event_id": "test-event-1", "sg_message_id": "test-msg-1"},
            {"email": "test@example.test", "timestamp": NOW - 30, "event": "delivered", "sg_event_id": "test-event-2", "sg_message_id": "test-msg-1", "response": "250 OK"},
        ]
        body = compact(events) + "\r\n"
        spam = compact([{"email": "test@example.test", "timestamp": NOW - 30, "event": "spamreport", "sg_event_id": "test-event-3"}]) + "\r\n"
        expected = {"status": 200, "events": [{"type": "processed", "id": "test-event-1"}, {"type": "delivered", "id": "test-event-2"}]}
        cases = [
            case("batch of two events", body, expected, sign(body)),
            case("an old timestamp is accepted (SendGrid states no window and retries for 24 hours)", body, expected, sign(body, ts=NOW - 86000)),
            case("spamreport event", spam, {"status": 200, "events": [{"type": "spamreport", "id": "test-event-3"}]}, sign(spam)),
            case("body without the trailing newline it was signed with", body.rstrip("\r\n"), {"status": 401}, sign(body)),
            case("tampered body", body.replace("delivered", "bounce"), {"status": 401}, sign(body)),
            case("signed by another key", body, {"status": 401}, sign(body, key=keys[1])),
            case("timestamp changed after signing", body, {"status": 401}, {**sign(body), "X-Twilio-Email-Event-Webhook-Timestamp": str(NOW - 19)}),
            case("missing signature", body, {"status": 401}, {k: v for k, v in sign(body).items() if k != "X-Twilio-Email-Event-Webhook-Signature"}),
            case("signature that is not base64", body, {"status": 401}, {**sign(body), "X-Twilio-Email-Event-Webhook-Signature": "not base64 !!"}),
            case("valid signature over a body that is not an array", '{"event":"open"}', {"status": 400}, sign('{"event":"open"}')),
            case("valid signature over malformed JSON", "[{", {"status": 400}, sign("[{")),
        ]
    write("sendgrid", {"publicKey": public}, cases)


def without(headers, *names):
    return {k: v for k, v in headers.items() if k not in names}


def published(slug):
    with open(os.path.join(ROOT, "data", "providers", f"{slug}.json"), encoding="utf-8") as f:
        return json.load(f)["signature"]["published_test_vector"]


# ---- Stripe ------------------------------------------------------------------------------------
# Stripe-Signature: t=<unix>,v1=<hex HMAC-SHA256(secret, "<t>.<raw body>")>[,v1=...][,v0=...]; only v1
# counts; Stripe's libraries allow five minutes (data/providers/stripe.json).

def stripe():
    secret = "whsec_test_stripe_endpoint_secret"
    tol = 300

    def signed(body, ts=NOW - 10, keys=(secret,), v0=False):
        parts = [f"t={ts}"] + ["v1=" + hmac("sha256", k, f"{ts}.".encode() + body.encode()).hex() for k in keys]
        if v0:
            parts.append("v0=" + "6f" * 32)
        return {"Content-Type": "application/json; charset=utf-8", "Stripe-Signature": ",".join(parts)}

    event = compact({"id": "evt_test_1", "object": "event", "created": NOW - 12, "type": "payment_intent.succeeded", "livemode": False,
                     "data": {"object": {"id": "pi_test_1", "object": "payment_intent", "amount": 4900, "currency": "usd", "status": "succeeded"}}})
    ok = {"status": 200, "type": "payment_intent.succeeded", "id": "evt_test_1"}
    v0_only = {**signed(event), "Stripe-Signature": f"t={NOW - 10},v0=" + hmac("sha256", secret, f"{NOW - 10}.".encode() + event.encode()).hex()}
    cases = [
        case("event", event, ok, signed(event)),
        case("test event with a fake v0 signature as well", event, ok, signed(event, v0=True)),
        case("two v1 signatures while a rolled secret is active", event, ok, signed(event, keys=("test-old-stripe-secret", secret))),
        case("timestamp at the edge of five minutes", event, ok, signed(event, ts=NOW - tol)),
        case("timestamp too old", event, {"status": 401}, signed(event, ts=NOW - tol - 1)),
        case("timestamp too far ahead", event, {"status": 401}, signed(event, ts=NOW + tol + 1)),
        case("only a v0 signature (never valid)", event, {"status": 401}, v0_only),
        case("tampered body", event.replace("4900", "1"), {"status": 401}, signed(event)),
        case("wrong secret", event, {"status": 401}, signed(event, keys=("test-wrong-secret",))),
        case("re-serialised JSON", event.replace(",", ", "), {"status": 401}, signed(event)),
        case("missing signature", event, {"status": 401}, without(signed(event), "Stripe-Signature")),
        case("header without a timestamp", event, {"status": 401}, {**signed(event), "Stripe-Signature": signed(event)["Stripe-Signature"].split(",", 1)[1]}),
        case("malformed JSON with a valid signature", "{not json", {"status": 400}, signed("{not json")),
        case("signed JSON without an event id", '{"type":"x"}', {"status": 400}, signed('{"type":"x"}')),
    ]
    write("stripe", {"secret": secret, "toleranceSeconds": tol}, cases)


# ---- GitHub ------------------------------------------------------------------------------------
# X-Hub-Signature-256: sha256=<hex HMAC-SHA256(secret, raw body)>; event in X-GitHub-Event, delivery
# id in X-GitHub-Delivery (data/providers/github.json).

def github():
    secret = "test-github-webhook-secret"

    def signed(body, event="push", key=secret, delivery="00000000-0000-4000-8000-000000000001"):
        return {"Content-Type": "application/json", "User-Agent": "GitHub-Hookshot/test", "X-GitHub-Event": event,
                "X-GitHub-Delivery": delivery, "X-GitHub-Hook-ID": "123",
                "X-Hub-Signature-256": "sha256=" + hmac("sha256", key, body.encode()).hex()}

    push = compact({"ref": "refs/heads/main", "before": "0" * 40, "after": "1" * 40,
                    "repository": {"id": 1, "full_name": "example/test-repo"}, "pusher": {"name": "test-user"}})
    ping = compact({"zen": "Test zen.", "hook_id": 123, "hook": {"type": "Repository", "id": 123, "active": True, "events": ["push"]}})
    issue = compact({"action": "opened", "issue": {"number": 7, "title": "Test issue"}, "repository": {"id": 1, "full_name": "example/test-repo"}})
    guid = "00000000-0000-4000-8000-000000000001"
    sha1_only = {**without(signed(push), "X-Hub-Signature-256"), "X-Hub-Signature": "sha1=" + hmac("sha1", secret, push.encode()).hex()}
    cases = [
        case("push", push, {"status": 200, "type": "push", "action": None, "id": guid}, signed(push)),
        case("ping when the webhook is created", ping, {"status": 200, "type": "ping", "action": None, "id": guid}, signed(ping, event="ping")),
        case("issues event with an action", issue, {"status": 200, "type": "issues", "action": "opened", "id": guid}, signed(issue, event="issues")),
        case("redelivery keeps the delivery id", push, {"status": 200, "type": "push", "id": guid}, signed(push)),
        case("only the SHA-1 header", push, {"status": 401}, sha1_only),
        case("signature without the sha256= prefix", push, {"status": 401}, {**signed(push), "X-Hub-Signature-256": hmac("sha256", secret, push.encode()).hex()}),
        case("tampered body", push.replace("main", "prod"), {"status": 401}, signed(push)),
        case("wrong secret", push, {"status": 401}, signed(push, key="test-wrong-secret")),
        case("no secret configured on the webhook (no signature header)", push, {"status": 401}, without(signed(push), "X-Hub-Signature-256")),
        case("missing event header", push, {"status": 400}, without(signed(push), "X-GitHub-Event")),
        case("malformed JSON with a valid signature", "{not json", {"status": 400}, signed("{not json")),
    ]
    pv = published("github")
    v = pv["value"]
    pub = [case("published example (GitHub docs)", v["payload"], {"status": 200, "verified": True},
                {"X-Hub-Signature-256": v["signature"]}, verifyOnly=True, secret=v["secret"], source=pv["source_url"], read=pv["read"])]
    write("github", {"secret": secret}, cases, pub)


# ---- Shopify -----------------------------------------------------------------------------------
# X-Shopify-Hmac-Sha256: base64 HMAC-SHA256(app client secret, raw body); topic in X-Shopify-Topic,
# delivery id in X-Shopify-Webhook-Id (data/providers/shopify.json).

def shopify():
    secret = "test-shopify-client-secret"

    def signed(body, topic="orders/create", key=secret, webhook_id="test-webhook-id-1"):
        return {"Content-Type": "application/json", "X-Shopify-Topic": topic, "X-Shopify-Hmac-Sha256": b64(hmac("sha256", key, body.encode())),
                "X-Shopify-Shop-Domain": "test-shop.myshopify.com", "X-Shopify-API-Version": "2026-07", "X-Shopify-Webhook-Id": webhook_id,
                "X-Shopify-Event-Id": "test-event-id-1", "X-Shopify-Triggered-At": "2026-10-09T08:53:10.000Z"}

    order = compact({"id": 820982911946154508, "email": "test@example.test", "total_price": "49.00", "currency": "USD",
                     "updated_at": "2026-10-09T08:53:10-04:00"})
    redact = compact({"shop_id": 954889, "shop_domain": "test-shop.myshopify.com", "customer": {"id": 191167, "email": "test@example.test"}, "orders_to_redact": [299938]})
    ok = {"status": 200, "type": "orders/create", "id": "test-webhook-id-1"}
    cases = [
        case("orders/create", order, ok, signed(order)),
        case("header names in lower case (HTTP/2)", order, ok, {k.lower(): v for k, v in signed(order).items()}),
        case("mandatory compliance topic customers/redact", redact, {"status": 200, "type": "customers/redact", "id": "test-webhook-id-2"},
             signed(redact, topic="customers/redact", webhook_id="test-webhook-id-2")),
        case("tampered body", order.replace("49.00", "0.01"), {"status": 401}, signed(order)),
        case("wrong secret", order, {"status": 401}, signed(order, key="test-wrong-secret")),
        case("hex digest instead of base64", order, {"status": 401}, {**signed(order), "X-Shopify-Hmac-Sha256": hmac("sha256", secret, order.encode()).hex()}),
        case("missing signature", order, {"status": 401}, without(signed(order), "X-Shopify-Hmac-Sha256")),
        case("missing topic", order, {"status": 400}, without(signed(order), "X-Shopify-Topic")),
        case("missing webhook id", order, {"status": 400}, without(signed(order), "X-Shopify-Webhook-Id")),
        case("malformed JSON with a valid signature", "{not json", {"status": 400}, signed("{not json")),
    ]
    write("shopify", {"secret": secret}, cases)


# ---- WooCommerce -------------------------------------------------------------------------------
# X-WC-Webhook-Signature: base64 HMAC-SHA256(webhook secret, raw body); topic in X-WC-Webhook-Topic;
# an unsigned ping "webhook_id=<id>" when a webhook is activated (data/providers/woocommerce.json).

def woocommerce():
    secret = "test-woocommerce-webhook-secret"

    def signed(body, topic="order.created", key=secret):
        resource, event = topic.split(".", 1)
        return {"Content-Type": "application/json", "User-Agent": "WooCommerce/test Hookshot (WordPress/test)",
                "X-WC-Webhook-Source": "https://shop.example.test/", "X-WC-Webhook-Topic": topic, "X-WC-Webhook-Resource": resource,
                "X-WC-Webhook-Event": event, "X-WC-Webhook-ID": "12", "X-WC-Webhook-Delivery-ID": "test-delivery-1",
                "X-WC-Webhook-Signature": b64(hmac("sha256", key, body.encode()))}

    order = compact({"id": 727, "status": "processing", "currency": "USD", "total": "49.00", "date_modified_gmt": "2026-10-09T08:53:10"})
    ok = {"status": 200, "type": "order.created", "id": "test-delivery-1"}
    cases = [
        case("order.created", order, ok, signed(order)),
        case("ping on activation (unsigned, form-style body)", "webhook_id=12", {"status": 200, "type": "ping", "id": None},
             {"User-Agent": "WooCommerce/test Hookshot (WordPress/test)"}),
        case("unsigned JSON body", order, {"status": 401}, without(signed(order), "X-WC-Webhook-Signature")),
        case("ping-shaped body with extra text is not a ping", "webhook_id=12&x=1", {"status": 401}, {}),
        case("tampered body", order.replace("49.00", "0.01"), {"status": 401}, signed(order)),
        case("wrong secret", order, {"status": 401}, signed(order, key="test-wrong-secret")),
        case("missing topic", order, {"status": 400}, without(signed(order), "X-WC-Webhook-Topic")),
        case("malformed JSON with a valid signature", "{not json", {"status": 400}, signed("{not json")),
    ]
    write("woocommerce", {"secret": secret}, cases)


# ---- Lemon Squeezy -----------------------------------------------------------------------------
# X-Signature: hex HMAC-SHA256(signing secret, raw body); event in X-Event-Name and in the signed
# body's meta.event_name (data/providers/lemonsqueezy.json).

def lemonsqueezy():
    secret = "test-lemon-secret-42"

    def signed(body, name="order_created", key=secret):
        return {"Content-Type": "application/json", "X-Event-Name": name, "X-Signature": hmac("sha256", key, body.encode()).hex()}

    order = compact({"meta": {"event_name": "order_created", "custom_data": {"user_id": "test-42"}},
                     "data": {"type": "orders", "id": "1001", "attributes": {"status": "paid", "total": 4900}}})
    ok = {"status": 200, "type": "order_created", "id": None, "resource": "orders/1001"}
    cases = [
        case("order_created", order, ok, signed(order)),
        case("event header missing: the signed body names the event", order, ok, without(signed(order), "X-Event-Name")),
        case("event header disagrees with the signed body", order, {"status": 400}, signed(order, name="order_refunded")),
        case("tampered body", order.replace("4900", "1"), {"status": 401}, signed(order)),
        case("wrong secret", order, {"status": 401}, signed(order, key="test-wrong-secret")),
        case("missing signature", order, {"status": 401}, without(signed(order), "X-Signature")),
        case("signed JSON without meta.event_name", '{"data":{}}', {"status": 400}, signed('{"data":{}}')),
        case("malformed JSON with a valid signature", "{not json", {"status": 400}, signed("{not json")),
    ]
    write("lemonsqueezy", {"secret": secret}, cases)


# ---- Paddle ------------------------------------------------------------------------------------
# Paddle-Signature: ts=<unix>;h1=<hex HMAC-SHA256(secret key string, "<ts>:<raw body>")>[;h1=...];
# Paddle's SDKs allow five seconds (data/providers/paddle.json).

def paddle():
    secret = "pdl_ntfset_test_0000000000000000_testsecretkey"
    tol = 5

    def signed(body, ts=NOW - 1, keys=(secret,)):
        parts = [f"ts={ts}"] + ["h1=" + hmac("sha256", k, f"{ts}:".encode() + body.encode()).hex() for k in keys]
        return {"Content-Type": "application/json", "Paddle-Signature": ";".join(parts)}

    event = compact({"event_id": "evt_test_1", "event_type": "transaction.completed", "occurred_at": "2026-10-09T08:53:10.000000Z",
                     "notification_id": "ntf_test_1", "data": {"id": "txn_test_1", "status": "completed"}})
    ok = {"status": 200, "type": "transaction.completed", "id": "evt_test_1"}
    cases = [
        case("event", event, ok, signed(event)),
        case("two h1 signatures during a secret change", event, ok, signed(event, keys=("pdl_ntfset_test_old", secret))),
        case("timestamp at the edge of five seconds", event, ok, signed(event, ts=NOW - tol)),
        case("timestamp too old", event, {"status": 401}, signed(event, ts=NOW - tol - 1)),
        case("timestamp too far ahead", event, {"status": 401}, signed(event, ts=NOW + tol + 1)),
        case("tampered body", event.replace("completed", "canceled"), {"status": 401}, signed(event)),
        case("wrong secret", event, {"status": 401}, signed(event, keys=("pdl_ntfset_test_wrong",))),
        case("re-serialised JSON", event.replace(",", ", "), {"status": 401}, signed(event)),
        case("missing signature", event, {"status": 401}, without(signed(event), "Paddle-Signature")),
        case("header without h1", event, {"status": 401}, {**signed(event), "Paddle-Signature": f"ts={NOW - 1}"}),
        case("malformed JSON with a valid signature", "{not json", {"status": 400}, signed("{not json")),
    ]
    write("paddle", {"secret": secret, "toleranceSeconds": tol}, cases)


# ---- Resend ------------------------------------------------------------------------------------
# Standard Webhooks with svix-* headers: svix-signature "v1,<base64 HMAC-SHA256(base64-decoded secret
# after whsec_, "<svix-id>.<svix-timestamp>.<raw body>")>", space separated; five minutes in Resend's SDK
# (data/providers/resend.json).

def resend():
    key = bytes(range(40, 64))
    secret = "whsec_" + b64(key)
    tol = 300

    def signed(body, msg_id="msg_test_1", ts=NOW - 5, k=key, extra_first=None):
        sig = "v1," + b64(hmac("sha256", k, f"{msg_id}.{ts}.".encode() + body.encode()))
        if extra_first:
            sig = extra_first + " " + sig
        return {"Content-Type": "application/json", "svix-id": msg_id, "svix-timestamp": str(ts), "svix-signature": sig}

    event = compact({"type": "email.delivered", "created_at": "2026-10-09T08:53:10.000Z",
                     "data": {"email_id": "test-email-1", "to": ["test@example.test"], "subject": "Test"}})
    ok = {"status": 200, "type": "email.delivered", "id": "msg_test_1"}
    cases = [
        case("event", event, ok, signed(event)),
        case("several signatures, one valid", event, ok, signed(event, extra_first="v1," + b64(b"not-this-one"))),
        case("timestamp at the edge of five minutes", event, ok, signed(event, ts=NOW - tol)),
        case("timestamp too old", event, {"status": 401}, signed(event, ts=NOW - tol - 1)),
        case("timestamp too far ahead", event, {"status": 401}, signed(event, ts=NOW + tol + 1)),
        case("message id changed after signing", event, {"status": 401}, {**signed(event), "svix-id": "msg_test_2"}),
        case("tampered body", event.replace("delivered", "bounced"), {"status": 401}, signed(event)),
        case("wrong secret", event, {"status": 401}, signed(event, k=bytes(24))),
        case("unknown signature version only", event, {"status": 401}, {**signed(event), "svix-signature": "v2," + signed(event)["svix-signature"][3:]}),
        case("missing id header", event, {"status": 401}, without(signed(event), "svix-id")),
        case("re-serialised JSON", event.replace(",", ", "), {"status": 401}, signed(event)),
        case("malformed JSON with a valid signature", "{not json", {"status": 400}, signed("{not json")),
    ]
    write("resend", {"secret": secret, "toleranceSeconds": tol}, cases)


# ---- PayPal ------------------------------------------------------------------------------------
# PAYPAL-TRANSMISSION-SIG: base64 RSA SHA-256 signature over
# "<transmission id>|<transmission time>|<webhook id>|<CRC32 of the raw body, decimal>", checked with the
# certificate at PAYPAL-CERT-URL; PAYPAL-AUTH-ALGO is SHA256withRSA (data/providers/paypal.json).
# The certificate is fetched only from an https URL on paypal.com or a subdomain: WebhookVault's rule,
# because PayPal does not state one and any other certificate lets anyone sign.

def paypal():
    webhook_id = "TEST-WEBHOOK-ID-1"
    cert_url = "https://api.sandbox.paypal.com/v1/notifications/certs/CERT-test-1"
    with tempfile.TemporaryDirectory() as tmp:
        def make_cert(name):
            k, c = os.path.join(tmp, f"{name}.key"), os.path.join(tmp, f"{name}.pem")
            openssl(["req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", k, "-out", c, "-subj", f"/CN=test-{name}", "-days", "3650"])
            with open(c, encoding="ascii") as f:
                return k, f.read()

        key, pem = make_cert("paypal-signing")
        other_key, _ = make_cert("other")

        def signed(body, k=key, url=cert_url, wid=webhook_id, algo="SHA256withRSA", tid="test-transmission-1", ttime="2026-10-09T08:53:12Z"):
            msg = os.path.join(tmp, "msg.bin")
            with open(msg, "wb") as f:
                f.write(f"{tid}|{ttime}|{wid}|{zlib.crc32(body.encode())}".encode())
            sig = b64(openssl(["dgst", "-sha256", "-sign", k, msg]))
            return {"Content-Type": "application/json", "PAYPAL-TRANSMISSION-ID": tid, "PAYPAL-TRANSMISSION-TIME": ttime,
                    "PAYPAL-TRANSMISSION-SIG": sig, "PAYPAL-CERT-URL": url, "PAYPAL-AUTH-ALGO": algo}

        event = compact({"id": "WH-TEST-1", "event_version": "1.0", "create_time": "2026-10-09T08:53:10.000Z", "resource_type": "capture",
                         "resource_version": "2.0", "event_type": "PAYMENT.CAPTURE.COMPLETED", "summary": "Payment completed",
                         "resource": {"id": "CAPTURE-TEST-1", "status": "COMPLETED"}})
        ok = {"status": 200, "type": "PAYMENT.CAPTURE.COMPLETED", "id": "WH-TEST-1"}
        evil = "https://certs.example.test/v1/notifications/certs/CERT-test-1"
        lookalike = "https://api.sandbox.paypal.com.example.test/v1/notifications/certs/CERT-test-1"
        missing = "https://api.sandbox.paypal.com/v1/notifications/certs/CERT-test-missing"
        certificates = {cert_url: pem, evil: pem, lookalike: pem, cert_url.replace("https:", "http:"): pem}
        cases = [
            case("event", event, ok, signed(event)),
            case("certificate URL on another host, even with a valid signature", event, {"status": 401}, signed(event, url=evil)),
            case("certificate URL on a look-alike host", event, {"status": 401}, signed(event, url=lookalike)),
            case("certificate URL over http", event, {"status": 401}, signed(event, url=cert_url.replace("https:", "http:"))),
            case("certificate cannot be fetched", event, {"status": 500}, signed(event, url=missing)),
            case("tampered body (CRC32 changes)", event.replace("COMPLETED", "DENIED"), {"status": 401}, signed(event)),
            case("signed for another webhook id", event, {"status": 401}, signed(event, wid="TEST-WEBHOOK-ID-2")),
            case("signed by a key that is not the certificate's", event, {"status": 401}, signed(event, k=other_key)),
            case("algorithm header other than SHA256withRSA", event, {"status": 401}, signed(event, algo="SHA1withRSA")),
            case("transmission id changed after signing", event, {"status": 401}, {**signed(event), "PAYPAL-TRANSMISSION-ID": "test-transmission-2"}),
            case("missing signature", event, {"status": 401}, without(signed(event), "PAYPAL-TRANSMISSION-SIG")),
            case("malformed JSON with a valid signature", "{not json", {"status": 400}, signed("{not json")),
        ]
    write("paypal", {"webhookId": webhook_id, "certificates": certificates}, cases)


# ---- Discord -----------------------------------------------------------------------------------
# X-Signature-Ed25519: hex Ed25519 signature over "<X-Signature-Timestamp><raw body>", checked with the
# application public key (hex). Webhook Events answer 204 (PING is type 0); the Interactions endpoint
# answers a PING (type 1) with {"type": 1} (data/providers/discord.json).

def discord():
    with tempfile.TemporaryDirectory() as tmp:
        keys = []
        for name in ("app", "other"):
            pem = os.path.join(tmp, f"{name}.pem")
            openssl(["genpkey", "-algorithm", "ed25519", "-out", pem])
            keys.append(pem)
        public = openssl(["pkey", "-in", keys[0], "-pubout", "-outform", "DER"])[-32:].hex()

        def signed(body, ts=str(NOW - 5), k=keys[0]):
            msg = os.path.join(tmp, "msg.bin")
            with open(msg, "wb") as f:
                f.write(ts.encode() + body.encode())
            sig = openssl(["pkeyutl", "-sign", "-inkey", k, "-rawin", "-in", msg]).hex()
            return {"Content-Type": "application/json", "X-Signature-Ed25519": sig, "X-Signature-Timestamp": ts}

        ev_ping = compact({"version": 1, "application_id": "1234567890", "type": 0})
        ev_auth = compact({"version": 1, "application_id": "1234567890", "type": 1,
                           "event": {"type": "APPLICATION_AUTHORIZED", "timestamp": "2026-10-09T08:53:10.000000+00:00",
                                     "data": {"integration_type": 0, "scopes": ["applications.commands"], "user": {"id": "111", "username": "test-user"}}}})
        in_ping = compact({"id": "2222222222", "application_id": "1234567890", "type": 1, "token": "test-interaction-token", "version": 1})
        in_cmd = compact({"id": "3333333333", "application_id": "1234567890", "type": 2, "token": "test-interaction-token", "version": 1,
                          "data": {"id": "444", "name": "test", "type": 1}})
        cases = [
            case("webhook events: PING answered 204 after verifying", ev_ping, {"status": 204, "type": "PING"}, signed(ev_ping), mechanism="events"),
            case("webhook events: PING with an invalid signature (Discord's check)", ev_ping, {"status": 401}, signed(ev_ping, k=keys[1]), mechanism="events"),
            case("webhook events: APPLICATION_AUTHORIZED", ev_auth, {"status": 204, "type": "APPLICATION_AUTHORIZED"}, signed(ev_auth), mechanism="events"),
            case("webhook events: tampered body", ev_auth.replace("test-user", "other-user"), {"status": 401}, signed(ev_auth), mechanism="events"),
            case("webhook events: timestamp changed after signing", ev_auth, {"status": 401}, {**signed(ev_auth), "X-Signature-Timestamp": str(NOW - 4)}, mechanism="events"),
            case("webhook events: signature that is not hex", ev_auth, {"status": 401}, {**signed(ev_auth), "X-Signature-Ed25519": "zz" * 64}, mechanism="events"),
            case("webhook events: missing signature", ev_auth, {"status": 401}, without(signed(ev_auth), "X-Signature-Ed25519"), mechanism="events"),
            case("webhook events: malformed JSON with a valid signature", "{not json", {"status": 400}, signed("{not json"), mechanism="events"),
            case("interactions: PING answered with type 1", in_ping, {"status": 200, "type": 1, "id": "2222222222", "reply": '{"type":1}'}, signed(in_ping), mechanism="interactions"),
            case("interactions: PING with an invalid signature (Discord's check)", in_ping, {"status": 401}, signed(in_ping, k=keys[1]), mechanism="interactions"),
            case("interactions: application command", in_cmd, {"status": 200, "type": 2, "id": "3333333333", "reply": None}, signed(in_cmd), mechanism="interactions"),
            case("interactions: tampered body", in_cmd.replace('"test"', '"other"'), {"status": 401}, signed(in_cmd), mechanism="interactions"),
        ]
    write("discord", {"publicKey": public}, cases)


PROVIDERS = {"slack": slack, "twilio": twilio, "sendgrid": sendgrid, "stripe": stripe, "github": github, "shopify": shopify,
             "woocommerce": woocommerce, "lemonsqueezy": lemonsqueezy, "paddle": paddle, "resend": resend, "paypal": paypal,
             "discord": discord}

if __name__ == "__main__":
    wanted = sys.argv[1:] or list(PROVIDERS)
    unknown = [w for w in wanted if w not in PROVIDERS]
    if unknown:
        sys.exit(f"no vectors defined for: {', '.join(unknown)}")
    for slug in wanted:
        PROVIDERS[slug]()
