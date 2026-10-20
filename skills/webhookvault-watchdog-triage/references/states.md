# Watchdog timing

Read from https://docs.webhookvault.net/documentation/watchdogs on 2026-10-20.

- **Interval**: how long may pass between matching captures before the stream is late.
- **Grace**: the jitter tolerated before it is a problem. A daily payout that usually lands at 02:00
  does not need an alarm at 02:01.
- **Match**: optional criteria a capture must satisfy to count, in the transformation rule grammar.
  Without it, every capture counts.

A watchdog moves through its states on the clock:

```
last match ---- interval ----> overdue ---- grace ----> alarmed
                                                          |
                         matching capture arrives --------+--> recovered --(one interval)--> ok
```

- `overdue` is silent by design: it is the grace period.
- `alarmed` sends one alert and stays until traffic returns; it does not repeat on every check.
- `recovered` sends one alert and returns to `ok` after one interval. Alarm and recovery go out as
  the same incident.

## Cadence is the owner's choice

The person sets the interval and grace. On request, WebhookVault proposes an interval from what the
endpoint actually received; with too little history it says so. A watchdog created on an endpoint
with history starts from that history, so a stream that has been steady is `ok` from the start.

## Plans

Watchdogs start on the Solo plan. Alerts reach the technical contacts by email on every plan; Slack,
PagerDuty and the other channels start on Pro. A workspace with more watchdogs than its plan allows
keeps the extra ones in the `plan` state, unjudged.
