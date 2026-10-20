# What each `diagnose_endpoint` finding means

## Contents

- Severity and order
- Endpoint state findings
- Traffic and verification findings
- Delivery findings
- Rule findings
- Watchdog and alert findings
- Other findings

Read from the server's own finding codes on 2026-10-20. Each finding carries `code`, `severity`,
`title`, `evidence` (ids, counts, times) and `next` (the tool to call, with its arguments). Follow
`next` before guessing.

## Severity and order

Findings come most serious first: `error`, then `warning`, then `info`. No finding at all means the
endpoint looks healthy end to end; the problem is then usually on the sender's side or inside the
receiver after a successful delivery.

## Endpoint state findings

| Code | Meaning | Next |
|---|---|---|
| `endpoint_expired` | A temporary endpoint passed its expiry and answers senders 404 | Create a new one if still testing |
| `endpoint_off_by_plan` | The plan switched the endpoint off (more endpoints than slots); senders get 410 and nothing is stored | `get_usage` shows the slots; a person upgrades or frees a slot |
| `endpoint_off` | A person switched the endpoint off; senders get 410 and nothing is stored | A person switches it on in the app |
| `endpoint_expiring` | A temporary endpoint expires within the hour | Finish the test or create a new one |

A 410 or 404 answer tells most senders to stop or retry later; requests sent while the endpoint
was off were not stored and cannot be recovered from WebhookVault. Ask the sender to re-send.

## Traffic and verification findings

| Code | Meaning | Next |
|---|---|---|
| `no_traffic` | No request in the last 24 hours, or never | The sender's side: see nothing-arrived.md |
| `verification_failing` | At least 10% of requests failed the signature check | The secret or scheme; the `webhookvault-check-verification` skill |
| `payloads_over_cap` | Some bodies were over the plan's size cap; only a placeholder was stored | Those requests cannot be replayed; a larger plan stores them |

## Delivery findings

| Code | Meaning | Next |
|---|---|---|
| `deliveries_failing` | At least 20% of finished deliveries did not succeed | `get_endpoint_errors` groups them by action, host, status and error class |
| `dead_letters` | Deliveries used up their retries and are parked | Fix the receiver, then replay with the person's agreement |
| `deliveries_interrupted` | Sends were cut off mid-flight | Usually a WebhookVault restart; they are retried |
| `no_actions` | The endpoint stores requests but sends them nowhere | A person adds an action if delivery is expected |
| `actions_all_off` | Every action is switched off | A person switches one on |

## Rule findings

| Code | Meaning | Next |
|---|---|---|
| `rule_disabled` | A transformation rule kept faulting and was switched off automatically | `get_transformations` for the rule and why; a person fixes and re-enables it |
| `rule_faulting` | A transformation rule is faulting on deliveries | `get_transformations`, then `preview_transformation` on a failing request |

## Watchdog and alert findings

| Code | Meaning |
|---|---|
| `watchdog_alarmed` | A watchdog alarmed: the webhooks it waits for stopped arriving |
| `watchdog_overdue` | A watchdog is overdue and alarms when its grace runs out |
| `watchdog_endpoint_off` | A watchdog watches a switched-off endpoint, so it cannot alarm |
| `watchdog_plan` | A watchdog is paused because the plan has fewer watchdog slots |
| `alert_channel_failing` | An alert channel is failing; alarms fall back to email |
| `alerts_email_only` | Alarms reach people by email only, or only the workspace owners |

## Other findings

| Code | Meaning |
|---|---|
| `recent_changes` | The endpoint's configuration changed in the last 24 hours; `list_audit_events` shows what and who |
