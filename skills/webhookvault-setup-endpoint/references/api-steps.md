# Creating an endpoint with the API

Read from https://docs.webhookvault.net/documentation/quickstart and the published OpenAPI document
(https://app.webhookvault.net/openapi/v1.json, operation `createEndpoint`) on 2026-10-20.

The API needs a plan with API access (Solo and up) and a **Developer access** key, created on the
API keys page of the app. Keep it in an environment variable; never paste it into a chat.

```bash
curl -s https://app.webhookvault.net/api/v1/endpoints \
  -H "Authorization: Bearer $WV_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"payments production","provider":"stripe"}'
```

The response includes `id` and the capture `url`.

Fields the create call accepts include:

| Field | Meaning |
|---|---|
| `name` | Up to 30 characters |
| `provider` | A provider slug from the catalogue (`GET /api/v1/providers`); omit for a generic endpoint |
| `signingSecret` | The provider's signing secret, for verification; never returned afterwards |
| `ttlSeconds` | 60 to 86,400: makes the endpoint expire and be deleted (for tests and CI) |
| `forwardUrl` | Forward every capture to this URL |
| `forwardSigningSecret` | Sign forwarded deliveries with `wv-signature` |

The full list, with the custom response and manual signature scheme fields, is in the API reference
at https://docs.webhookvault.net/api-reference. Pass secrets from environment variables in a script,
never as literals in a file that is committed.

An unknown provider slug is refused with a message naming it; `list_providers` on the MCP server, or
`GET /api/v1/providers`, gives the valid slugs.
