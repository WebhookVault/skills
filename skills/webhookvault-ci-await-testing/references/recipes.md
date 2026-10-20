# CI recipes

## Contents

- bash with curl and jq
- Node.js (no dependencies)
- Python (no dependencies)
- A job definition

Each reads the Developer access key from the environment variable `WV_KEY`, set from the CI
system's secret store. Replace `./trigger-the-thing` and the assertions with the system under test.
The API base is `https://app.webhookvault.net/api/v1`.

## bash with curl and jq

```bash
set -euo pipefail
API=https://app.webhookvault.net/api/v1
AUTH="Authorization: Bearer $WV_KEY"

EP=$(curl -sf "$API/endpoints" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"name\":\"ci-${CI_JOB_ID:-local}\",\"ttlSeconds\":900}")
EP_ID=$(echo "$EP" | jq -r .id)
EP_URL=$(echo "$EP" | jq -r .url)

./trigger-the-thing "$EP_URL"

RESULT=$(curl -s -w '\n%{http_code}' "$API/endpoints/$EP_ID/requests/await?afterId=0&q=order.created&timeoutSeconds=60" -H "$AUTH")
STATUS=$(echo "$RESULT" | tail -n 1)
BODY=$(echo "$RESULT" | sed '$d')
if [ "$STATUS" != "200" ]; then
  echo "No order.created webhook reached endpoint $EP_ID within 60 s (status $STATUS)." >&2
  exit 1
fi
echo "$BODY" | jq -e '.body | fromjson | .type == "order.created"' > /dev/null
```

## Node.js (no dependencies)

Node 18 or later (global `fetch`).

```js
const API = "https://app.webhookvault.net/api/v1";
const headers = { Authorization: `Bearer ${process.env.WV_KEY}`, "Content-Type": "application/json" };

async function main() {
  const created = await fetch(`${API}/endpoints`, {
    method: "POST", headers,
    body: JSON.stringify({ name: `ci-${process.env.CI_JOB_ID ?? "local"}`, ttlSeconds: 900 }),
  });
  if (!created.ok) throw new Error(`Creating the endpoint failed with ${created.status}`);
  const endpoint = await created.json();

  await triggerTheThing(endpoint.url);

  const url = `${API}/endpoints/${endpoint.id}/requests/await?afterId=0&q=order.created&timeoutSeconds=60`;
  const res = await fetch(url, { headers });
  if (res.status === 204) throw new Error(`No order.created webhook reached ${endpoint.id} within 60 s`);
  if (!res.ok) throw new Error(`Await failed with ${res.status}`);

  const request = await res.json();
  const payload = JSON.parse(request.body);
  if (payload.type !== "order.created") throw new Error(`Unexpected event type ${payload.type}`);
}

main().catch((err) => { console.error(err.message); process.exit(1); });
```

## Python (no dependencies)

```python
import json, os, sys, urllib.request

API = "https://app.webhookvault.net/api/v1"
HEADERS = {"Authorization": f"Bearer {os.environ['WV_KEY']}", "Content-Type": "application/json"}

def call(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    with urllib.request.urlopen(req, timeout=90) as res:
        return res.status, res.read()

status, raw = call("POST", f"{API}/endpoints", {"name": f"ci-{os.environ.get('CI_JOB_ID', 'local')}", "ttlSeconds": 900})
endpoint = json.loads(raw)

trigger_the_thing(endpoint["url"])

status, raw = call("GET", f"{API}/endpoints/{endpoint['id']}/requests/await?afterId=0&q=order.created&timeoutSeconds=60")
if status == 204:
    sys.exit(f"No order.created webhook reached {endpoint['id']} within 60 s")
payload = json.loads(json.loads(raw)["body"])
assert payload["type"] == "order.created", f"Unexpected event type {payload['type']}"
```

`urllib` raises `HTTPError` for 4xx and 5xx answers, which fails the job with the status.

## A job definition

The same three steps fit any CI system. In GitHub Actions, for example:

```yaml
jobs:
  webhook-contract:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Assert the webhook fires
        env:
          WV_KEY: ${{ secrets.WV_KEY }}
          CI_JOB_ID: ${{ github.run_id }}
        run: ./scripts/assert-webhook.sh
```

Keep the key in the CI system's secret store and pass it as an environment variable; never echo it.
