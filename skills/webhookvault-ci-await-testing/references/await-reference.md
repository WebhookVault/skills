# The await call

Read from https://docs.webhookvault.net/documentation/ci-testing and the published OpenAPI
document (https://app.webhookvault.net/openapi/v1.json, operation `awaitRequest`) on 2026-10-20.

`GET /api/v1/endpoints/{endpointId}/requests/await`, header `Authorization: Bearer <Developer key>`.

| Parameter | Meaning |
|---|---|
| `timeoutSeconds` | How long to block: 1 to 80, default 30 |
| `q` | Text the request must contain |
| `method` | HTTP method |
| `state` | Delivery state |
| `verification` | Verification verdict |
| `since` | Match requests received at or after this instant instead of only future ones |
| `afterId` | Match requests with an id greater than this instead of only future ones; `0` accepts anything stored |

| Status | Meaning |
|---|---|
| `200` | The matching request, as soon as it arrived |
| `204` | Nothing matching arrived within `timeoutSeconds` |
| `400` | A parameter is invalid |
| `401` | No key, or the key is unknown or revoked |
| `403` | The key may not do this (for example an Agent access key, or a plan without API access) |
| `404` | No such endpoint in this workspace |
| `429` | The key's rate budget is spent; honour `Retry-After` |

The call waits server-side and wakes on arrival, so a match returns at once.

## The race

By default only requests arriving after the call starts match. When the webhook can fire before
the await begins (a fast system, a slow runner), read the newest stored id first and pass it as
`afterId`:

```bash
LAST_ID=$(curl -s "https://app.webhookvault.net/api/v1/endpoints/$EP_ID/requests?pageSize=1" \
  -H "Authorization: Bearer $WV_KEY" | jq -r '.items[0].id // 0')
./trigger-the-thing
curl -s "https://app.webhookvault.net/api/v1/endpoints/$EP_ID/requests/await?afterId=$LAST_ID&timeoutSeconds=60" \
  -H "Authorization: Bearer $WV_KEY"
```

On a fresh endpoint created by the job, `afterId=0` is enough.
