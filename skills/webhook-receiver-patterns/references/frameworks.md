# Raw bodies and size limits per framework

## Express (Node.js)

- `express.raw({ type: () => true, limit: 256 * 1024 })` on the webhook route gives `req.body` as a
  Buffer and refuses a larger body with a 413 error (type `entity.too.large`) passed to the error
  handler. Answer it as JSON from an error handler; never send a stack trace.
- Register the webhook route before any global `express.json()`, or the JSON parser consumes the
  body first and `req.body` becomes an object.
- Express 5 passes errors thrown in an async handler to the error handler.

## FastAPI and Starlette (Python)

- Read `await request.body()`, or stream `request.stream()` to count bytes as they arrive. Starlette
  sets no body size limit of its own, so the receiver (or the server or proxy in front) must.
- Never declare the payload as a Pydantic model parameter on the webhook route: FastAPI would read
  and parse it before your code runs.
- Answer with `JSONResponse` and an explicit status code.

## ASP.NET Core

- Take `HttpRequest` and read `request.Body` into bytes; do not bind the body to a model parameter.
- Kestrel limits a request body to about 30 MB by default. Set a smaller limit for the webhook
  route, or count bytes while reading as the example does, which holds under any server.
- Middleware that reads the body before the endpoint must call `request.EnableBuffering()` and rewind
  `request.Body.Position = 0`.

## Behind a proxy or gateway

- A reverse proxy may have its own body limit (nginx `client_max_body_size`); keep it at or above
  the receiver's, so the receiver's answer is the one the sender sees.
- A gateway that decompresses, re-encodes or pretty-prints the body breaks every body signature.
- URL-bound signature schemes need the public URL from configuration, not the URL the app sees.
