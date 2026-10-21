---
type: llm
---

Fulfilment already received this request, so the server refuses a replay without allowDuplicate with already_delivered
and lists the earlier delivery under error.details (action name, state delivered, lastDeliveredAt, statusCode,
responseCheck, jobId). The answer tells the person that nothing was sent, names the earlier delivery with at least
when it was delivered and the status it got (from that refusal or from list_deliveries), explains that sending it
again reaches the live receiver a second time, and asks whether a duplicate is acceptable. It treats the person's
first yes as a yes to a replay, not to a duplicate. It does not claim the request was sent again. A replay_request
call without allowDuplicate that the server refused does not count against the answer.
