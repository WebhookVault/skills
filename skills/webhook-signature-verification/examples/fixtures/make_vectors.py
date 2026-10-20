"""Builds vectors.json: signed webhook samples for every scheme family, computed by the openssl
command line, never by the example code under test. The Node.js, Python and C# examples are each
checked against this file, so a test never only checks an implementation against itself.

    python make_vectors.py            (needs openssl 3 on PATH)

Every secret and key here is a test value made for these vectors. The key-pair schemes use keys
generated for this run; only the public halves and the signatures are written out.
"""

import base64
import json
import os
import subprocess
import tempfile

# A fixed clock for the vectors; tests pass it as "now", so freshness checks are deterministic.
NOW = 1760000000


def openssl(args, data):
    return subprocess.run(["openssl", *args], input=data, capture_output=True, check=True).stdout


def hmac(algo, key_bytes, data):
    """HMAC by openssl, with the key given as hex so any byte value works."""
    return openssl(["dgst", f"-{algo}", "-mac", "HMAC", "-macopt", f"hexkey:{key_bytes.hex()}", "-binary"], data)


def hx(b):
    return b.hex()


def b64(b):
    return base64.b64encode(b).decode()


bodies = {
    "json": b'{"id":"evt_test_1","type":"order.created","data":{"total":4900}}',
    "unicode": '{"id":"evt_test_2","note":"café ✓ 日本"}'.encode("utf-8"),
    "empty": b"",
    "spacing": b'{ "id" : "evt_test_3",\n  "type": "order.paid" }\n',
}

vectors = []


def add(family, name, **fields):
    vectors.append({"family": family, "name": name, "now": NOW, **fields, "note": "test values only"})


# 1. HMAC over the raw body: hex with a prefix (GitHub style) and base64 (Shopify style).
secret = "test-secret-raw-body"
for kind, body in bodies.items():
    mac = hmac("sha256", secret.encode(), body)
    add("hmac-body", f"hex-prefixed-{kind}", secret=secret, body=body.decode("utf-8"),
        signature="sha256=" + hx(mac), encoding="hex", prefix="sha256=")
    add("hmac-body", f"base64-{kind}", secret=secret, body=body.decode("utf-8"),
        signature=b64(mac), encoding="base64", prefix="")

# 2. Timestamped HMAC, header "t=<ts>,v1=<hex>" over "<ts>.<body>" (Stripe style), with a second
#    v1 entry as during a secret rotation.
#    The same family with "ts=<ts>;h1=<hex>" over "<ts>:<body>" (Paddle style).
secret = "test-secret-timestamped"
styles = [
    {"style": "comma", "pairSeparator": ",", "timestampKey": "t", "signatureKey": "v1", "joiner": "."},
    {"style": "semicolon", "pairSeparator": ";", "timestampKey": "ts", "signatureKey": "h1", "joiner": ":"},
]
for s in styles:
    for kind, body in bodies.items():
        ts = str(NOW - 30)
        signed = ts.encode() + s["joiner"].encode() + body
        mac = hx(hmac("sha256", secret.encode(), signed))
        other = hx(hmac("sha256", b"test-old-secret", signed))
        sep, tk, sk = s["pairSeparator"], s["timestampKey"], s["signatureKey"]
        add("hmac-timestamp-header", f"{s['style']}-{kind}", secret=secret, body=body.decode("utf-8"),
            header=f"{tk}={ts}{sep}{sk}={other}{sep}{sk}={mac}", tolerance=300,
            **{k: v for k, v in s.items() if k != "style"})

# 3. Timestamp in its own header, "v0:<ts>:<body>", signature "v0=<hex>" (Slack style).
secret = "test-secret-versioned"
for kind, body in bodies.items():
    ts = str(NOW - 10)
    mac = hx(hmac("sha256", secret.encode(), b"v0:" + ts.encode() + b":" + body))
    add("hmac-versioned-timestamp", kind, secret=secret, body=body.decode("utf-8"),
        timestamp=ts, signature="v0=" + mac, tolerance=300)

# 4. Standard Webhooks: base64 secret after "whsec_", signed "<id>.<ts>.<body>", "v1,<base64>".
key = bytes(range(1, 33))
secret = "whsec_" + b64(key)
for kind, body in bodies.items():
    ts = str(NOW - 5)
    msg_id = f"msg_test_{kind}"
    mac = b64(hmac("sha256", key, msg_id.encode() + b"." + ts.encode() + b"." + body))
    add("standard-webhooks", kind, secret=secret, body=body.decode("utf-8"), id=msg_id,
        timestamp=ts, signature=f"v1,{b64(b'not-this-one')} v1,{mac}", tolerance=300)

# 5. URL-bound HMAC-SHA1 over the full URL plus form parameters sorted by name (Twilio style).
token = "test-auth-token"
url = "https://example.test/hooks/sms?tenant=7"
params = {"To": "+15550001111", "From": "+15550002222", "Body": "Hi é", "MessageSid": "SMtest1"}
signed = url + "".join(k + params[k] for k in sorted(params))
add("hmac-url-form", "form", secret=token, url=url, params=params,
    signature=b64(hmac("sha1", token.encode(), signed.encode("utf-8"))))

# 6 and 7. Key pairs: Ed25519 over "<ts><body>" (hex signature, raw hex public key, Discord style)
#          and ECDSA P-256 with SHA-256 over "<ts><body>" (base64 DER signature, base64 SPKI key,
#          SendGrid style). Keys are generated for this run and the private halves discarded.
with tempfile.TemporaryDirectory() as tmp:
    ed_key = os.path.join(tmp, "ed.pem")
    openssl(["genpkey", "-algorithm", "ed25519", "-out", ed_key], b"")
    ed_pub_der = openssl(["pkey", "-in", ed_key, "-pubout", "-outform", "DER"], b"")
    ed_pub_raw = ed_pub_der[-32:]
    ec_key = os.path.join(tmp, "ec.pem")
    openssl(["genpkey", "-algorithm", "EC", "-pkeyopt", "ec_paramgen_curve:P-256", "-out", ec_key], b"")
    ec_pub_der = openssl(["pkey", "-in", ec_key, "-pubout", "-outform", "DER"], b"")

    for kind, body in bodies.items():
        ts = str(NOW - 20)
        message = ts.encode() + body
        msg_file = os.path.join(tmp, "msg.bin")
        with open(msg_file, "wb") as f:
            f.write(message)
        ed_sig = openssl(["pkeyutl", "-sign", "-inkey", ed_key, "-rawin", "-in", msg_file], b"")
        add("ed25519", kind, publicKey=hx(ed_pub_raw), body=body.decode("utf-8"), timestamp=ts,
            signature=hx(ed_sig), tolerance=300)
        ec_sig = openssl(["dgst", "-sha256", "-sign", ec_key, msg_file], b"")
        add("ecdsa-p256", kind, publicKey=b64(ec_pub_der), body=body.decode("utf-8"), timestamp=ts,
            signature=b64(ec_sig), tolerance=300)

# 8. A shared token in a header: no signature, compared in constant time.
add("shared-token", "token", secret="test-shared-token-value", signature="test-shared-token-value")

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vectors.json")
with open(out, "w", encoding="utf-8", newline="\n") as f:
    f.write("[\n" + ",\n".join(json.dumps(v, ensure_ascii=False) for v in vectors) + "\n]\n")
print(f"wrote {len(vectors)} vectors to {out}")
