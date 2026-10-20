# How `await_request` waits

Read from the server's tool description on 2026-10-20.

- It watches one endpoint and returns as soon as a matching request arrives, or answers
  `arrived: false` after `timeoutSeconds` (1 to 55, default 30).
- **Without `afterId`**, only requests arriving after the call starts count, and the newest match
  is returned. A request that landed a moment before the call is not seen.
- **With `afterId`**, the first request after that id (from the last 7 days) is returned. Calling
  again with the returned id walks the stream one request at a time without skipping any.
- Filters: `method` (for example POST) and `text` (up to 200 characters, matched in the path and
  query, and in bodies too on plans with full payload search).
- A key may hold 2 waits at once and a workspace 4; over that the call answers `busy`.
- If the key is revoked or suspended while waiting, the call ends with `key_revoked` and returns
  nothing.

## Closing the race

When the person triggers the sender before the wait starts, the request may land first and be
missed. To be sure:

1. Before triggering, call `search_requests(endpointId, limit)` with a limit of 1 and note the
   newest id (or 0 when there is none).
2. Trigger the sender.
3. Call `await_request(endpointId, afterId)` with that id.

## When nothing arrives

`arrived: false` is an answer, not a failure. Call again while the person is still testing. After
two or three empty waits, check the sender's side (the URL pasted, the event selected, test or
live mode) before waiting longer.
