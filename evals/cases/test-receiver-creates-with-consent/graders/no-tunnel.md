---
type: regex
pattern: 'ngrok|cloudflared|localtunnel|\btunnel'
flags: i
match: not_contains
target: last_message
---
