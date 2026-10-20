# Getting the raw body, per framework

A signature covers the bytes the sender sent. Read them before anything parses or reformats them,
verify, and only then parse.

## Express (Node.js)

Give the webhook route its own raw parser, ahead of any global `express.json()`:

```js
app.post("/webhooks", express.raw({ type: "*/*" }), handler); // req.body is a Buffer
```

A global `app.use(express.json())` registered before this route consumes the body first; register
the webhook route before it or exclude the path.

## Next.js route handlers

```js
export async function POST(request) {
  const raw = Buffer.from(await request.arrayBuffer());
  // verify raw, then JSON.parse(raw.toString("utf8"))
}
```

Read the body once: `request.json()` after `arrayBuffer()` fails, and the reverse loses the bytes.

## Fastify

Register a content-type parser that keeps the buffer for the webhook route, for example
`addContentTypeParser("application/json", { parseAs: "buffer" }, (req, body, done) => done(null, body))`
in a plugin scoped to that route.

## FastAPI and Starlette (Python)

```python
@app.post("/webhooks")
async def webhooks(request: Request):
    raw = await request.body()  # bytes, exactly as received
    # verify raw, then json.loads(raw)
```

Do not declare the payload as a Pydantic model parameter on this route: FastAPI would parse it
before your code runs.

## Flask

`request.get_data()` returns the raw bytes; call it before `request.get_json()`.

## Django

`request.body` is the raw bytes. Read it before `request.POST` for form-encoded senders.

## ASP.NET Core

```csharp
app.MapPost("/webhooks", async (HttpRequest request) =>
{
    using var buffer = new MemoryStream();
    await request.Body.CopyToAsync(buffer);
    var raw = buffer.ToArray();
    // verify raw, then JsonSerializer.Deserialize<T>(raw)
});
```

Do not bind the body to a model parameter on this endpoint. When middleware must read the body
too, call `request.EnableBuffering()` first and rewind `request.Body.Position = 0`.

## Form-encoded senders

Some senders post `application/x-www-form-urlencoded`. For body-signing schemes, verify the raw
bytes. For URL-bound schemes that sign the form fields, use the decoded field values exactly as
sent, sorted as the sender's documentation says.

## Proxies and gateways

A gateway that decompresses, re-encodes or pretty-prints JSON breaks every body signature. Check
that the body length you verify equals the `Content-Length` the sender sent.
