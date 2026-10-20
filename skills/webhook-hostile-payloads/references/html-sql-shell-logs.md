# HTML, SQL, shells and logs

## HTML

- Use the template engine's automatic escaping and never turn it off for payload text.
- Escape `&`, `<`, `>`, `"` and `'` in text and in quoted attribute values.
- Never place payload text inside `<script>`, `<style>`, an event attribute (`onclick`), or a URL
  attribute without validating the scheme (`javascript:` URLs). A link from a payload is shown as
  text, or allowed only for `https:` after parsing.
- Admin dashboards and support tools that show raw webhooks are a common target: the people viewing
  them have privileges.

## SQL

- Parameters for every value. Payload text never becomes part of the query string.
- Identifiers (table or column names) are never taken from a payload. Map payload values to a fixed
  allowlist of identifiers.
- A `LIKE` search with payload text needs its `%` and `_` escaped as well as parameterised.

## Shells and processes

- Do not pass payload text through a shell. Call the process API with an argument array
  (`execFile`, `subprocess.run([...])`, `ProcessStartInfo.ArgumentList`).
- A filename from a payload is not a path: never join it to a directory without checking it cannot
  escape (`..`, absolute paths, drive letters).

## Logs

- One entry per line: replace CR, LF, other control characters and U+2028 and U+2029 with visible
  escapes, or log as structured JSON where the logger escapes values itself.
- Cap long values.
- Never log signing secrets, signature headers, authorization headers, cookies or tokens. Redact by
  header name before logging a request.

## Redaction

Redact credentials before payloads are stored for display, shown in a dashboard, sent to an alert
channel, or given to an assistant: header names such as `authorization`, `cookie`, names containing
`token`, `secret`, `signature`, `key`, and query parameters of the same names. Mask card numbers to
their last four digits. Redaction is for display; the original stays in the protected store if the
system needs it.
