# When nothing arrived at WebhookVault

If `search_requests` finds nothing in the window and the endpoint is active, the request never
reached the capture URL. WebhookVault stores every request that reaches an active endpoint, so the
cause is on the sender's side or on the way to WebhookVault. Work through these with the person;
each is a question about their sender's settings, which the assistant cannot see.

1. **The URL.** Compare the URL configured at the sender with the endpoint's capture URL from
   `get_endpoint`. Look for a copy of an older endpoint's URL, a different environment, a missing
   path segment, or `http` against `https`. A capture URL may carry a sub-path after the endpoint
   id; the sub-path is kept and shows in `search_requests`.
2. **The events.** Many senders send only the events a webhook subscribes to. Check that the event
   the person expects is selected, and that it actually happened in the sender (a test-mode event
   does not fire a live-mode webhook, and the reverse).
3. **Test mode and live mode.** Senders such as payment providers keep separate webhook settings,
   secrets and events per mode. The webhook may be configured in the other mode.
4. **The sender's delivery log.** Most providers show their own delivery attempts with the status
   they received. A 410 or 404 there means the endpoint was off, expired or the URL is wrong; a
   timeout or connection error there with nothing captured is worth reporting to WebhookVault with
   the time.
5. **The window.** Searches default to the last 24 hours. Widen `since` when the event is older,
   and remember the sender may have queued retries for hours.
6. **What does arrive.** `describe_traffic` lists the event names and paths the endpoint does
   receive. A similar but differently named event often explains "it never came".
7. **A provider test.** Many providers have a "send test webhook" button. If a test arrives and the
   real event does not, the URL is right and the subscription or mode is the cause.

If the sender's log shows a successful delivery to the right URL at a time when `search_requests`
shows nothing, give the person the exact time and the sender's request id, and suggest contacting
WebhookVault support with them.
