# Connecting a client to the WebhookVault MCP server

Server URL: `https://mcp.webhookvault.net` (Streamable HTTP). Authentication: the header
`Authorization: Bearer <Agent access key>`. A person creates the key on the API keys page of the
app (https://app.webhookvault.net) by choosing **Agent access**; the page then shows these same
setups with the key filled in. Replace `YOUR_AGENT_KEY` below with the key. Never paste a key into
a chat with an assistant.

## Claude Code

```bash
claude mcp add --transport http --scope user webhookvault https://mcp.webhookvault.net \
  --header "Authorization: Bearer YOUR_AGENT_KEY"
```

`--scope user` makes it available in every project; leave it out for the current project only.
In Claude Code, `/mcp` lists webhookvault as connected.

## Cursor

Add to `~/.cursor/mcp.json` (every project) or `.cursor/mcp.json` (one project):

```json
{
  "mcpServers": {
    "webhookvault": {
      "url": "https://mcp.webhookvault.net",
      "headers": { "Authorization": "Bearer YOUR_AGENT_KEY" }
    }
  }
}
```

To keep the key out of the file, set `WEBHOOKVAULT_KEY` in the environment and write
`"Bearer ${env:WEBHOOKVAULT_KEY}"` instead.

## VS Code

Run **MCP: Open User Configuration** from the command palette and add the server. VS Code asks for
the key the first time the server starts and keeps it in its secret store:

```json
{
  "inputs": [
    { "type": "promptString", "id": "webhookvault-key", "description": "WebhookVault Agent access key", "password": true }
  ],
  "servers": {
    "webhookvault": {
      "type": "http",
      "url": "https://mcp.webhookvault.net",
      "headers": { "Authorization": "Bearer ${input:webhookvault-key}" }
    }
  }
}
```

## Codex

Codex reads the key from an environment variable. In the shell profile:

```bash
export WEBHOOKVAULT_KEY="YOUR_AGENT_KEY"
```

then in `~/.codex/config.toml`:

```toml
[mcp_servers.webhookvault]
url = "https://mcp.webhookvault.net"
bearer_token_env_var = "WEBHOOKVAULT_KEY"
```

## Other clients

Any MCP client that connects to a remote server over Streamable HTTP and can send a header: server
URL `https://mcp.webhookvault.net`, header `Authorization: Bearer YOUR_AGENT_KEY`.

claude.ai and Claude desktop add servers as connectors that sign in instead of sending a key,
which this server does not offer. Use the key with Claude Code instead.

## Which key

| Key kind | Works with | Refused by |
|---|---|---|
| Agent access | The MCP server only | The API (`agent_key_not_accepted`) |
| Developer access | The API (`/api/v1`) only | The MCP server (`developer_key_not_accepted`) |

Both kinds act on the whole workspace and use its API key slots. The full guide is at
https://docs.webhookvault.net/documentation/mcp.
